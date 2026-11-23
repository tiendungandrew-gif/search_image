import asyncio
from contextlib import aclosing
from time import perf_counter

from app.services.rag.citation_validator import render_answer, validate_selection
from app.services.rag.llm_provider import ChatProvider, NativeGeminiProvider, ProviderError


class Generator:
    def __init__(self, settings):
        self.settings = settings
        self.provider = None
        self.error_code = "RAG_DISABLED"
        self.inflight = 0
        if settings.rag_enabled:
            try:
                provider = (
                    NativeGeminiProvider
                    if settings.rag_model_provider == "gemini"
                    and settings.rag_gemini_api_style == "native"
                    else ChatProvider
                )
                self.provider = provider(settings)
                self.error_code = None
            except ProviderError as error:
                self.error_code = error.code

    async def close(self):
        if self.provider:
            await self.provider.close()

    async def run(self, context, language, answer, latency, emit):
        answer.context = context.summary
        answer.prompt_sha256 = context.prompt_sha256
        answer.prompt_version = (
            "extractive-facts-compact-v1"
            if context.summary.get("format") == "compact"
            else "extractive-facts-v1"
        )
        answer.provider = self.settings.rag_model_provider
        answer.model_id = self.settings.rag_model_id or None
        answer.model_revision = self.settings.rag_model_revision
        answer.generation_config = {
            key: getattr(self.settings, "rag_" + key)
            for key in [
                "temperature",
                "max_input_tokens",
                "max_context_tokens",
                "max_output_tokens",
                "timeout_seconds",
                "provider_retries",
                "streaming_enabled",
                "reasoning_effort",
                "token_parameter",
                "max_concurrency",
                "gemini_api_style",
            ]
        }
        if self.error_code:
            answer.error_code = self.error_code
            return
        if not context.facts:
            answer.grounding_status = "insufficient_evidence"
            answer.answer = render_answer([], language)
            return
        if self.inflight >= self.settings.rag_max_concurrency:
            answer.error_code = "RAG_BUSY"
            return
        self.inflight += 1
        started = perf_counter()
        text = ""
        first = last = None
        try:
            await emit(
                "generation_started", {"provider": answer.provider, "model_id": answer.model_id}
            )
            async with (
                asyncio.timeout(self.settings.rag_timeout_seconds),
                aclosing(
                    self.provider.stream(
                        context.messages, streaming=self.settings.rag_streaming_enabled
                    )
                ) as stream,
            ):
                async for chunk in stream:
                    if chunk.text:
                        now = perf_counter()
                        first = first or now
                        last = now
                        text += chunk.text
                        if len(text.encode()) > 16384:
                            raise ProviderError("LLM_OUTPUT_LIMIT")
                        # Actual deltas; unvalidated output is never displayed as an answer.
                        await emit(
                            "token",
                            {"text": chunk.text, "verified": False, "kind": "evidence_selection"},
                        )
                    answer.usage = chunk.usage or answer.usage
                    answer.returned_model = chunk.returned_model or answer.returned_model
            validation = perf_counter()
            citations = validate_selection(text, context)
            answer.citations = citations
            answer.answer = render_answer(citations, language)
            answer.generated = True
            technical = {"width", "height", "media_type", "source_dataset", "license"}
            answer.grounding_status = (
                "supported"
                if citations
                and context.summary["technical_question"]
                and all(c.evidence_field in technical for c in citations)
                else "partially_supported"
                if citations
                else "insufficient_evidence"
            )
            answer.limitations.append(
                "Exact metadata quotations are validated; "
                "visual truth and answer relevance are not independently verified."
            )
            latency["validation_ms"] = (perf_counter() - validation) * 1000
        except (TimeoutError, ProviderError) as error:
            answer.error_code = error.code if isinstance(error, ProviderError) else "LLM_TIMEOUT"
            answer.grounding_status = "generation_unavailable"
            answer.citations = []
            await emit("error", {"code": answer.error_code, "retrieval_preserved": True})
        finally:
            self.inflight -= 1
            latency["generation_ms"] = (perf_counter() - started) * 1000
            observed = self.settings.rag_streaming_enabled
            latency["provider_ttft_ms"] = (first - started) * 1000 if first and observed else None
            latency["provider_ttlast_ms"] = (last - started) * 1000 if last and observed else None
