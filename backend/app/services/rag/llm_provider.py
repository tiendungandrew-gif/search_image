"""Bounded Chat Completions adapter for Gemini/OpenAI/self-hosted endpoints."""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class ProviderChunk:
    text: str = ""
    usage: dict | None = None
    returned_model: str | None = None


class ChatProvider:
    def __init__(self, settings, transport=None):
        self.settings = settings
        url = urlsplit(settings.rag_model_endpoint)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not settings.rag_model_id.strip()
        ):
            raise ProviderError("RAG_INVALID_CONFIG")
        if settings.rag_model_provider != "openai_compatible" and not (
            settings.rag_api_key and settings.rag_api_key.get_secret_value().strip()
        ):
            raise ProviderError("RAG_KEY_MISSING")
        if settings.rag_model_provider == "gemini" and (
            url.scheme != "https" or url.hostname != "generativelanguage.googleapis.com"
        ):
            raise ProviderError("RAG_INVALID_CONFIG")
        if settings.rag_model_provider == "openai" and (
            url.scheme != "https" or url.hostname != "api.openai.com"
        ):
            raise ProviderError("RAG_INVALID_CONFIG")
        headers = {}
        if settings.rag_api_key:
            headers["Authorization"] = "Bearer " + settings.rag_api_key.get_secret_value()
        self.client = httpx.AsyncClient(
            base_url=settings.rag_model_endpoint.rstrip("/") + "/",
            headers=headers,
            timeout=settings.rag_timeout_seconds,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=settings.rag_max_concurrency),
            transport=transport,
        )

    async def close(self):
        await self.client.aclose()

    async def stream(self, messages, *, streaming=True) -> AsyncIterator[ProviderChunk]:
        settings = self.settings
        body = {
            "model": settings.rag_model_id,
            "messages": messages,
            "temperature": settings.rag_temperature,
            settings.rag_token_parameter: settings.rag_max_output_tokens,
            "stream": streaming,
            "response_format": {"type": "json_object"},
        }
        if settings.rag_model_provider == "openai":
            body["store"] = False
        if settings.rag_reasoning_effort:
            body["reasoning_effort"] = settings.rag_reasoning_effort
        if streaming:
            body["stream_options"] = {"include_usage": True}
        for attempt in range(settings.rag_provider_retries + 1):
            try:
                async with self.client.stream("POST", "chat/completions", json=body) as response:
                    if (
                        response.status_code in {429, 500, 502, 503}
                        and attempt < settings.rag_provider_retries
                    ):
                        await response.aclose()
                        await asyncio.sleep(0.1)
                        continue
                    if response.status_code != 200:
                        code = {
                            401: "LLM_AUTH_FAILED",
                            403: "LLM_ACCESS_DENIED",
                            404: "LLM_MODEL_UNAVAILABLE",
                            429: "LLM_RATE_LIMITED",
                        }.get(response.status_code, "LLM_PROVIDER_ERROR")
                        raise ProviderError(code)
                    received = 0
                    if not streaming:
                        data = await response.aread()
                        if len(data) > 65536:
                            raise ProviderError("LLM_OUTPUT_LIMIT")
                        value = json.loads(data)
                        text = value["choices"][0]["message"]["content"]
                        if not isinstance(text, str):
                            raise ProviderError("LLM_INVALID_RESPONSE")
                        yield ProviderChunk(text, value.get("usage"), value.get("model"))
                        return
                    finished = False
                    async for line in response.aiter_lines():
                        received += len(line.encode())
                        if received > 131072 or len(line) > 65536:
                            raise ProviderError("LLM_OUTPUT_LIMIT")
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            finished = True
                            break
                        value = json.loads(raw)
                        choices = value.get("choices", [])
                        text = choices[0].get("delta", {}).get("content") if choices else ""
                        if text is not None and not isinstance(text, str):
                            raise ProviderError("LLM_INVALID_RESPONSE")
                        yield ProviderChunk(text or "", value.get("usage"), value.get("model"))
                    if not finished:
                        raise ProviderError("LLM_INCOMPLETE_STREAM")
                    return
            except ProviderError:
                raise
            except httpx.TimeoutException:
                raise ProviderError("LLM_TIMEOUT") from None
            except httpx.HTTPError:
                raise ProviderError("LLM_CONNECTION_FAILED") from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise ProviderError("LLM_INVALID_RESPONSE") from None

    async def generate(self, messages):
        output = []
        async for chunk in self.stream(messages, streaming=False):
            output.append(chunk)
        return output


class NativeGeminiProvider(ChatProvider):
    """Native GenerateContent; same bounded provider interface and citation policy."""

    def __init__(self, settings, transport=None):
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,160}", settings.rag_model_id):
            raise ProviderError("RAG_INVALID_CONFIG")
        if urlsplit(settings.rag_model_endpoint).path.rstrip("/") != "/v1beta":
            raise ProviderError("RAG_INVALID_CONFIG")
        super().__init__(settings, transport)
        self.client.headers.pop("authorization", None)
        self.client.headers["x-goog-api-key"] = settings.rag_api_key.get_secret_value()

    async def stream(self, messages, *, streaming=True):
        cfg = self.settings
        generation = {
            "temperature": cfg.rag_temperature,
            "maxOutputTokens": cfg.rag_max_output_tokens,
            "responseMimeType": "application/json",
        }
        if cfg.rag_reasoning_effort:
            generation["thinkingConfig"] = (
                {"thinkingBudget": 0}
                if cfg.rag_reasoning_effort == "none"
                else {"thinkingLevel": cfg.rag_reasoning_effort}
            )
        body = {
            "systemInstruction": {
                "parts": [{"text": m["content"]} for m in messages if m["role"] == "system"]
            },
            "contents": [
                {
                    "role": "model" if m["role"] == "assistant" else "user",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
                if m["role"] != "system"
            ],
            "generationConfig": generation,
        }
        method = "streamGenerateContent" if streaming else "generateContent"
        for attempt in range(cfg.rag_provider_retries + 1):
            try:
                async with self.client.stream(
                    "POST",
                    f"models/{cfg.rag_model_id}:{method}",
                    params={"alt": "sse"} if streaming else None,
                    json=body,
                ) as response:
                    if (
                        response.status_code in {429, 500, 502, 503}
                        and attempt < cfg.rag_provider_retries
                    ):
                        await response.aclose()
                        await asyncio.sleep(0.1)
                        continue
                    if response.status_code != 200:
                        raise ProviderError(
                            {
                                401: "LLM_AUTH_FAILED",
                                403: "LLM_ACCESS_DENIED",
                                404: "LLM_MODEL_UNAVAILABLE",
                                429: "LLM_RATE_LIMITED",
                            }.get(response.status_code, "LLM_PROVIDER_ERROR")
                        )
                    if not streaming:
                        raw = await response.aread()
                        if len(raw) > 65536:
                            raise ProviderError("LLM_OUTPUT_LIMIT")
                        chunk, _ = self.decode(json.loads(raw))
                        yield chunk
                        return
                    finished = False
                    received = 0
                    async for line in response.aiter_lines():
                        received += len(line.encode())
                        if received > 131072 or len(line) > 65536:
                            raise ProviderError("LLM_OUTPUT_LIMIT")
                        if line.startswith("data:"):
                            chunk, done = self.decode(json.loads(line[5:].strip()))
                            finished = finished or done
                            yield chunk
                    if not finished:
                        raise ProviderError("LLM_INCOMPLETE_STREAM")
                    return
            except ProviderError:
                raise
            except httpx.TimeoutException:
                raise ProviderError("LLM_TIMEOUT") from None
            except httpx.HTTPError:
                raise ProviderError("LLM_CONNECTION_FAILED") from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise ProviderError("LLM_INVALID_RESPONSE") from None

    @staticmethod
    def decode(value):
        candidates = value.get("candidates", [])
        candidate = candidates[0] if candidates else {}
        reason = candidate.get("finishReason")
        if reason and reason != "STOP":
            raise ProviderError("LLM_OUTPUT_REJECTED")
        text = "".join(
            p.get("text", "")
            for p in candidate.get("content", {}).get("parts", [])
            if not p.get("thought")
        )
        raw = value.get("usageMetadata")
        usage = (
            {
                "prompt_tokens": raw.get("promptTokenCount"),
                "completion_tokens": raw.get("candidatesTokenCount"),
                "total_tokens": raw.get("totalTokenCount"),
                "provider_metadata": raw,
            }
            if raw
            else None
        )
        return ProviderChunk(text, usage, value.get("modelVersion")), reason == "STOP"


class VisionProvider:
    """Future opt-in protocol boundary; no implementation sends image content."""

    async def describe(self, image_bytes):
        raise NotImplementedError("Vision grounding is not enabled in Phase08")
