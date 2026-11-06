import asyncio
from time import perf_counter
from uuid import uuid4

from app.core.exceptions import AppError
from app.schemas.rag import RagAnswer, RagResponse
from app.schemas.search import SearchRequest
from app.services.rag.context_builder import build_context, select_language
from app.services.rag.evidence_retriever import EvidenceRetriever
from app.services.search.search_service import SearchService


async def silent_emit(_event, _data):
    pass


class RagService:
    def __init__(self, runtime, generator):
        self.runtime = runtime
        self.generator = generator

    async def execute(self, request, request_id, emit=silent_emit):
        started = perf_counter()
        latency = {
            "retrieval_ms": 0.0,
            "evidence_ms": 0.0,
            "context_ms": 0.0,
            "generation_ms": 0.0,
            "validation_ms": 0.0,
            "provider_ttft_ms": None,
            "provider_ttlast_ms": None,
        }
        if (
            request.expected_index_id
            and request.expected_index_id != self.runtime.registry.index.id
        ):
            raise AppError(409, "INDEX_SWITCHING", "Chỉ mục đã đổi; hãy tìm kiếm lại")
        await emit(
            "retrieval_started",
            {"operation": "explain_existing" if request.image_ids else "search_and_explain"},
        )
        mark = perf_counter()
        search_result = None
        if request.image_ids is None:
            options = request.search or SearchRequest(
                query=request.query, search_mode=request.search_mode, top_k=request.top_k
            )
            async with asyncio.timeout(self.runtime.settings.request_timeout_seconds):
                search_result = await SearchService(self.runtime).execute(options, request_id)
            ids = [r.image_id for r in search_result.results]
        else:
            ids = request.image_ids
        latency["retrieval_ms"] = (perf_counter() - mark) * 1000
        mark = perf_counter()
        evidence, results, excluded = await EvidenceRetriever(self.runtime).retrieve(
            ids, search_result.results if search_result else None
        )
        latency["evidence_ms"] = (perf_counter() - mark) * 1000
        await emit(
            "retrieval_completed",
            {
                "results": [r.model_dump(mode="json") for r in results],
                "excluded_image_count": len(excluded),
            },
        )
        language = select_language(request)
        question = (
            request.question
            or request.query
            or (request.search.text if request.search else None)
            or (
                "Tóm tắt bằng chứng hiện có."
                if language == "vi"
                else "Summarize available evidence."
            )
        )
        mark = perf_counter()
        context = build_context(evidence, question, language, self.runtime.settings, request)
        latency["context_ms"] = (perf_counter() - mark) * 1000
        answer = RagAnswer(
            answer=(
                "Chưa tạo được giải thích lúc này. Kết quả ảnh vẫn có sẵn."
                if language == "vi"
                else "Explanation generation is unavailable. Image results remain available."
            ),
            grounding_status="generation_unavailable",
            evidence=(
                [e for e in evidence if str(e.image_id) in context.summary["included_image_ids"]]
                if context.facts
                else evidence[: self.runtime.settings.rag_max_evidence_items]
            ),
            language=language,
            limitations=["Text-only metadata explanation; no direct visual verification."],
        )
        await self.generator.run(context, language, answer, latency, emit)
        latency["total_ms"] = (perf_counter() - started) * 1000
        latency["time_to_last_token_from_request_ms"] = (
            latency["retrieval_ms"]
            + latency["evidence_ms"]
            + latency["context_ms"]
            + latency["provider_ttlast_ms"]
            if latency["provider_ttlast_ms"] is not None
            else None
        )
        warnings = list(search_result.warnings) if search_result else []
        if excluded:
            warnings.append(
                {
                    "code": "EVIDENCE_EXCLUDED",
                    "message": "Một số ảnh không còn đủ điều kiện truy xuất",
                }
            )
        return RagResponse(
            query_id=search_result.query_id if search_result else uuid4(),
            request_id=request_id,
            operation="search_and_explain" if search_result else "explain_existing",
            index_id=self.runtime.registry.index.id,
            model_id=self.runtime.registry.model.id,
            results=results,
            rag=answer,
            latency=latency,
            warnings=warnings,
        )
