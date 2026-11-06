import json
from collections import deque
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.core.auth import require_read_access
from app.core.exceptions import AppError
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search.search_service import SearchService

router = APIRouter(
    tags=["Search"],
    dependencies=[Depends(require_read_access)],
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
    options, data = await parse_input(request)
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


@router.get(
    "/system/search-metrics",
    summary="Bounded local full-response samples, không queries/credentials",
)
async def search_metrics(request: Request, limit: Annotated[int, Query(ge=1, le=10000)] = 1000):
    samples = getattr(request.app.state, "search_metrics", deque())
    return {"samples": list(samples)[-limit:], "capacity": 10000}
