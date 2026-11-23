import base64
import json
from collections import deque
from time import perf_counter
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.core.auth import charge_usage, require_diagnostics_access
from app.core.exceptions import AppError
from app.core.guest import charge_guest_search, require_search_access
from app.schemas.search import DiscoveryResponse, SearchRequest, SearchResponse
from app.services.search.search_service import SearchService

router = APIRouter(
    tags=["Search"],
    dependencies=[Depends(require_search_access)],
    responses={
        code: {"description": "Standard ErrorEnvelope"}
        for code in [400, 409, 413, 415, 422, 429, 500, 503, 504]
    },
)
BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/SearchRequest"}},
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "format": "binary"},
                        "options": {
                            "type": "string",
                            "description": "JSON SearchRequest; không trộn flat fields",
                        },
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 50},
                        "query": {"type": "string"},
                        "search_mode": {
                            "type": "string",
                            "enum": [
                                "semantic",
                                "image_similarity",
                                "multi_intent",
                                "multimodal",
                                "auto",
                            ],
                        },
                        "fusion_strategy": {
                            "type": "string",
                            "enum": ["rrf", "weighted_rrf", "weighted_score"],
                        },
                        "text_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "image_weight": {"type": "number", "minimum": 0, "maximum": 1},
                        "rerank": {"type": "boolean"},
                    },
                }
            },
        },
    }
}


async def parse_input(request):
    media = request.headers.get("content-type", "").split(";")[0].strip()
    data = None
    try:
        if media == "application/json":
            options = SearchRequest.model_validate_json(await request.body())
        elif media == "multipart/form-data":
            async with request.form(max_files=1, max_fields=12, max_part_size=65536) as form:
                if not set(form.keys()).issubset(
                    {
                        "image",
                        "options",
                        "top_k",
                        "search_mode",
                        "query",
                        "text",
                        "fusion_strategy",
                        "text_weight",
                        "image_weight",
                        "rerank",
                    }
                ) or any(len(form.getlist(k)) != 1 for k in form.keys()):
                    raise AppError(422, "INVALID_INPUT", "Multipart fields không hợp lệ")
                file = form.get("image")
                if file is not None and not isinstance(file, UploadFile):
                    raise AppError(422, "INVALID_INPUT", "Image field phải là file")
                if "options" in form and set(form.keys()) - {"image", "options"}:
                    raise AppError(422, "INVALID_INPUT", "Không trộn options và legacy form fields")
                if "options" in form:
                    values = json.loads(form["options"])
                else:
                    values = {k: v for k, v in form.items() if k != "image"}
                    for key in ["top_k", "text_weight", "image_weight", "rerank"]:
                        if key in values:
                            values[key] = json.loads(values[key])
                options = SearchRequest.model_validate(values)
                if file is not None:
                    data = await file.read(
                        request.app.state.settings.image_max_upload_mb * 1024**2 + 1
                    )
        else:
            raise AppError(415, "UNSUPPORTED_MEDIA", "Cần JSON hoặc multipart/form-data")
    except (ValueError, TypeError, ValidationError):
        raise AppError(422, "INVALID_INPUT", "Search input không hợp lệ") from None
    return options, data


async def run_search(request, multimodal_alias=False):
    mark = perf_counter()
    guest = request.state.principal.role == "guest"
    if guest and request.headers.get("content-type", "").startswith("multipart/"):
        raise AppError(401, "LOGIN_REQUIRED", "Đăng nhập để tìm kiếm bằng ảnh")
    options, data = await parse_input(request)
    if guest:
        if (
            data is not None
            or options.image_id is not None
            or options.mode not in {"auto", "text"}
            or options.constraints is not None
            or options.rerank.enabled
            or options.explain.enabled
            or options.require_verified
        ):
            raise AppError(401, "LOGIN_REQUIRED", "Đăng nhập để sử dụng chức năng này")
        if options.top_k > request.app.state.settings.guest_max_top_k or (
            options.candidate_count is not None and options.candidate_count > 50
        ):
            raise AppError(
                422,
                "GUEST_SEARCH_LIMIT",
                f"Khách được xem tối đa {request.app.state.settings.guest_max_top_k} ảnh mỗi lượt",
            )
        options = options.model_copy(
            update={
                "mode": "text",
                "retrieval_strategy": "fused",
                "candidate_count": options.candidate_count or 50,
            }
        )
    if (
        not multimodal_alias
        and options.text is not None
        and (data is not None or options.image_id is not None)
    ):
        raise AppError(422, "INVALID_INPUT", "Text+image dùng endpoint /search/multimodal")
    runtime = getattr(request.app.state, "search_runtime", None)
    if not request.app.state.settings.search_enabled:
        raise AppError(409, "FEATURE_DISABLED", "Semantic Search đang tắt")
    if runtime is None or not runtime.available:
        raise AppError(503, "NOT_READY", "Search model/index chưa sẵn sàng", retryable=True)
    if guest:
        await charge_guest_search(request)
    else:
        await charge_usage(request, "search")
    try:
        result = await SearchService(runtime).execute(options, request.state.request_id, data)
    except AppError:
        raise
    except (ValueError, RuntimeError):
        raise AppError(500, "INFERENCE_FAILED", "Encoder không tạo được vector hợp lệ") from None
    except Exception:
        raise AppError(
            503, "DEPENDENCY_UNAVAILABLE", "Search dependency không khả dụng", retryable=True
        ) from None
    total_processing = (perf_counter() - mark) * 1000
    result.latency["stages"]["input_validation_ms"] = total_processing - result.latency_ms
    result.latency["processing_ms"] = total_processing
    result.latency_ms = total_processing
    request.state.search_trace = {
        "query_id": str(result.query_id),
        "modality": result.search_mode,
        "model_id": str(result.model_id),
        "text_encoder_manifest_sha256": result.effective_settings.get(
            "text_encoder_manifest_sha256"
        ),
        "index_id": str(result.index_id),
        "stages": result.latency["stages"],
        "processing_ms": result.latency_ms,
        "route": result.effective_settings["route"],
        "vector_calls": result.effective_settings["vector_calls"],
        "rerank_applied": result.effective_settings["rerank_applied"],
    }
    request.state.result_ready_at = perf_counter()
    return result


@router.post(
    "/search",
    response_model=SearchResponse,
    openapi_extra=BODY,
    summary="CLIP text/image Semantic Search",
)
async def search(request: Request):
    return await run_search(request)


@router.post(
    "/search/multimodal",
    response_model=SearchResponse,
    openapi_extra=BODY,
    summary="Text/image/multimodal search với candidate fusion và optional reranking",
)
async def image_search(request: Request):
    return await run_search(request, multimodal_alias=True)


@router.post(
    "/search/voice",
    summary="Chuyển giọng nói thành văn bản tìm kiếm (Speech-to-Text)",
)
async def transcribe_voice_search(request: Request):
    settings = request.app.state.settings
    media = request.headers.get("content-type", "").split(";")[0].strip()
    if media != "multipart/form-data":
        raise AppError(415, "UNSUPPORTED_MEDIA", "Cần multipart/form-data chứa file âm thanh")
    try:
        async with request.form(max_files=1, max_fields=2, max_part_size=5 * 1024 * 1024) as form:
            audio_file = form.get("audio")
            if audio_file is None or not isinstance(audio_file, UploadFile):
                raise AppError(422, "INVALID_INPUT", "Thiếu dữ liệu âm thanh")
            raw_mime = (audio_file.content_type or "audio/webm").split(";")[0].strip().lower()
            allowed_mimes = {
                "audio/webm",
                "audio/ogg",
                "audio/wav",
                "audio/x-wav",
                "audio/wave",
                "audio/mp4",
                "audio/mpeg",
                "audio/mp3",
                "video/webm",
                "application/ogg",
            }
            if raw_mime not in allowed_mimes:
                raise AppError(415, "UNSUPPORTED_MEDIA", "Định dạng âm thanh không được hỗ trợ")
            mime_type = (
                "audio/webm"
                if raw_mime == "video/webm"
                else "audio/ogg"
                if raw_mime == "application/ogg"
                else "audio/wav"
                if raw_mime in {"audio/x-wav", "audio/wave"}
                else raw_mime
            )
            audio_bytes = await audio_file.read(5 * 1024 * 1024 + 1)
    except AppError:
        raise
    except Exception:
        raise AppError(422, "INVALID_INPUT", "Không đọc được dữ liệu âm thanh") from None
    if not audio_bytes or len(audio_bytes) < 64:
        raise AppError(422, "EMPTY_AUDIO", "Chưa nhận được âm thanh từ micro")
    if len(audio_bytes) > 5 * 1024 * 1024:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "Đoạn ghi âm vượt quá giới hạn 5 MB")
    api_key = (
        settings.rag_api_key.get_secret_value().strip()
        if settings.rag_api_key
        else settings.gemini_api_key.get_secret_value().strip()
        if settings.gemini_api_key
        else ""
    )
    model_id = settings.rag_model_id.strip() or "gemini-2.5-flash"
    if not api_key or settings.rag_model_provider != "gemini":
        raise AppError(
            503,
            "VOICE_UNAVAILABLE",
            "Dịch vụ nhận diện giọng nói chưa được cấu hình trên backend",
        )
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    generation: dict[str, object] = {
        "temperature": 0.0,
        "maxOutputTokens": 128,
        "responseMimeType": "application/json",
    }
    if settings.rag_reasoning_effort:
        generation["thinkingConfig"] = (
            {"thinkingBudget": 0}
            if settings.rag_reasoning_effort == "none"
            else {"thinkingLevel": settings.rag_reasoning_effort}
        )
    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "Bạn là bộ chuyển đổi giọng nói thành văn bản (Speech-to-Text) cho thanh "
                        "tìm kiếm ảnh. Hãy chép lại chính xác từ khóa hoặc câu người dùng nói "
                        "(tiếng Việt hoặc tiếng Anh). Không thêm lời giải thích, không đặt dấu "
                        "chấm câu thừa ở cuối, không tự bịa nội dung nếu âm thanh chỉ có tiếng ồn "
                        'hoặc im lặng. Trả về đúng JSON: {"transcript": "..."}. '
                        'Nếu không có lời nói rõ ràng thì trả về {"transcript": ""}.'
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Chép lại lời nói trong đoạn âm thanh này thành từ khóa tìm kiếm."},
                    {"inlineData": {"mimeType": mime_type, "data": encoded_audio}},
                ],
            }
        ],
        "generationConfig": generation,
    }
    endpoint = settings.rag_model_endpoint.rstrip("/")
    url = f"{endpoint}/models/{model_id}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
            if resp.status_code != 200:
                raise AppError(
                    503,
                    "VOICE_PROVIDER_ERROR",
                    "Không thể nhận diện giọng nói lúc này. Vui lòng thử lại.",
                    retryable=True,
                )
            data = resp.json()
            candidates = data.get("candidates") or []
            parts = (
                candidates[0].get("content", {}).get("parts", [])
                if candidates
                else []
            )
            raw_text = "".join(
                p.get("text", "") for p in parts if not p.get("thought")
            ).strip()
            transcript = ""
            if raw_text:
                try:
                    parsed = json.loads(raw_text)
                    if isinstance(parsed, dict) and isinstance(parsed.get("transcript"), str):
                        transcript = parsed["transcript"].strip()
                except ValueError:
                    transcript = raw_text.strip().strip('"')
    except AppError:
        raise
    except Exception:
        raise AppError(
            503,
            "VOICE_TRANSCRIPTION_FAILED",
            "Kết nối nhận diện giọng nói bị gián đoạn. Vui lòng thử lại.",
            retryable=True,
        ) from None
    return {"transcript": transcript}


@router.get(
    "/system/search-metrics",
    dependencies=[Depends(require_diagnostics_access)],
    summary="Bounded local full-response samples, không queries/credentials",
)
async def search_metrics(request: Request, limit: Annotated[int, Query(ge=1, le=10000)] = 1000):
    samples = getattr(request.app.state, "search_metrics", deque())
    return {"samples": list(samples)[-limit:], "capacity": 10000}


@router.get("/search/suggestions")
async def suggestions(
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=160)],
    limit: Annotated[int, Query(ge=1, le=8)] = 5,
    source_dataset: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
):
    from app.services.search.suggestions import search_suggestions

    return {
        "suggestions": await search_suggestions(
            request.app.state.services, q, limit, source_dataset
        )
    }


@router.get("/search/discovery", response_model=DiscoveryResponse)
async def discovery(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=50)] = 24,
    seed: UUID | None = None,
    cursor: Annotated[str | None, Query(
        pattern=r"^[0-9a-f]{32}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )] = None,
):
    from app.services.search.discovery import discover_images

    if request.state.principal.role == "guest":
        limit = min(limit, request.app.state.settings.guest_max_top_k)
    if cursor and seed is None:
        raise AppError(422, "INVALID_INPUT", "Thiếu mã phiên khám phá")
    return await discover_images(request.app.state.services, limit, seed, cursor)
