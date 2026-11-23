import asyncio
import json

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.core.auth import charge_usage, require_diagnostics_access, require_read_access
from app.core.exceptions import AppError
from app.schemas.rag import RagRequest, RagResponse
from app.services.rag.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["RAG"], dependencies=[Depends(require_read_access)])


def service(request):
    runtime = request.app.state.search_runtime
    if not runtime or not runtime.available:
        raise AppError(503, "NOT_READY", "Search model/index chưa sẵn sàng", retryable=True)
    return RagService(runtime, request.app.state.rag_generator)


def record(request, result):
    request.app.state.rag_metrics.append(
        {
            "request_id": request.state.request_id,
            "query_id": str(result.query_id),
            "grounding_status": result.rag.grounding_status,
            "error_code": result.rag.error_code,
            "generated": result.rag.generated,
            "provider": result.rag.provider,
            "model_id": result.rag.model_id,
            "returned_model": result.rag.returned_model,
            "prompt_sha256": result.rag.prompt_sha256,
            "latency": result.latency,
            "evidence_count": len(result.rag.evidence),
            "result_count": len(result.results),
            "usage": result.rag.usage,
        }
    )


@router.post("/explain", response_model=RagResponse)
async def explain(body: RagRequest, request: Request):
    await charge_usage(request, "rag")
    result = await service(request).execute(body, request.state.request_id)
    record(request, result)
    return result


@router.get("/status", dependencies=[Depends(require_diagnostics_access)])
async def status(request: Request):
    generator = request.app.state.rag_generator
    return {
        "enabled": request.app.state.settings.rag_enabled,
        "configured": generator.provider is not None,
        "error_code": generator.error_code,
        "provider": request.app.state.settings.rag_model_provider,
        "model_id": request.app.state.settings.rag_model_id,
        "streaming": request.app.state.settings.rag_streaming_enabled,
        "generation_config": {
            key: getattr(request.app.state.settings, "rag_" + key)
            for key in [
                "temperature",
                "max_input_tokens",
                "max_context_tokens",
                "max_output_tokens",
                "timeout_seconds",
                "request_timeout_seconds",
                "provider_retries",
                "reasoning_effort",
                "gemini_api_style",
            ]
        },
        "grounding_policy": "validated extractive metadata facts; no visual verification",
    }


@router.get("/samples", dependencies=[Depends(require_diagnostics_access)])
async def samples(request: Request):
    return {"samples": list(request.app.state.rag_metrics)}


@router.post(
    "/explain/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def stream(body: RagRequest, request: Request):
    await charge_usage(request, "rag")
    rag = service(request)
    if not request.app.state.settings.rag_streaming_enabled:
        raise AppError(409, "FEATURE_DISABLED", "RAG streaming đang tắt")

    async def events():
        queue = asyncio.Queue(maxsize=1024)

        async def emit(event, data):
            await queue.put((event, data))

        async def run():
            try:
                result = await rag.execute(body, request.state.request_id, emit)
                record(request, result)
                await emit("generation_completed", result.model_dump(mode="json"))
            except asyncio.CancelledError:
                raise
            except Exception as error:
                await emit(
                    "error", {"code": error.code if isinstance(error, AppError) else "RAG_FAILED"}
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )
