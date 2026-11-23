import asyncio
import json

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.core.auth import charge_usage, require_diagnostics_access, require_read_access
from app.core.exceptions import AppError
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent.errors import AgentError

router = APIRouter(
    prefix="/search/agent", tags=["Agent"], dependencies=[Depends(require_read_access)]
)


def service(request):
    agent = request.app.state.agent_service
    if not request.app.state.settings.agent_enabled or agent is None:
        raise AppError(409, "FEATURE_DISABLED", "Agent Search đang tắt")
    return agent


def record(request, result):
    request.app.state.agent_metrics.append(
        {
            "request_id": result.request_id,
            "query_id": str(result.query_id),
            "execution_id": str(result.execution_id),
            "status": result.status,
            "strategy": result.search_mode,
            "planner_mode": result.planner_mode,
            "planner_attempts": result.planner_attempts,
            "plan_id": str(result.plan_id) if result.plan_id else None,
            "planner_trace": [t.model_dump(mode="json") for t in result.planner_trace]
            if request.app.state.settings.agent_log_trace
            else [],
            "tool_calls": result.tool_calls,
            "logical_hops": result.logical_hops,
            "steps": [s.model_dump(mode="json") for s in result.steps]
            if request.app.state.settings.agent_log_trace
            else [],
            "image_count": len(result.results),
            "evidence_count": len(result.evidence),
            "latency": result.latency,
            "error_code": result.error_code,
        }
    )


@router.post("", response_model=AgentResponse)
async def search(body: AgentRequest, request: Request):
    await charge_usage(request, "agent")
    try:
        result = await service(request).execute(body, request.state.request_id)
    except AgentError as error:
        raise AppError(
            429 if error.code == "AGENT_BUSY" else 503,
            error.code,
            "Agent chưa thể xử lý yêu cầu",
            retryable=True,
        ) from None
    record(request, result)
    return result


@router.get("/status", dependencies=[Depends(require_diagnostics_access)])
async def status(request: Request):
    agent = request.app.state.agent_service
    return {
        "enabled": request.app.state.settings.agent_enabled,
        "initialized": agent is not None,
        "planner_mode": request.app.state.settings.agent_planner_mode,
        "llm_planning_enabled": request.app.state.settings.agent_llm_planning_enabled,
        "max_hops": request.app.state.settings.agent_max_hops,
        "max_tool_calls": request.app.state.settings.agent_max_tool_calls,
        "deadline_seconds": request.app.state.settings.agent_timeout_seconds,
        "tools": [d.public(request.app.state.settings) for d in agent.registry.values()]
        if agent
        else [],
        "dataset_status": await agent.knowledge.dataset_status(agent.runtime)
        if agent
        else "unknown",
        "knowledge_policy": "source-attributed verified relationships; no model-memory facts",
    }


@router.get("/samples", dependencies=[Depends(require_diagnostics_access)])
async def samples(request: Request):
    return {
        "samples": list(request.app.state.agent_metrics),
        "http_samples": list(request.app.state.agent_http_metrics),
    }


@router.post(
    "/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def stream(body: AgentRequest, request: Request):
    await charge_usage(request, "agent")
    agent = service(request)
    if not request.app.state.settings.agent_streaming_enabled:
        raise AppError(409, "FEATURE_DISABLED", "Agent streaming đang tắt")

    async def events():
        queue = asyncio.Queue(maxsize=256)
        closed = False

        async def emit(event, data):
            if not closed:
                await queue.put((event, data))

        async def execute():
            try:
                result = await agent.execute(body, request.state.request_id, emit)
                record(request, result)
                await emit(
                    "agent_completed" if result.status == "completed" else "agent_partial",
                    result.model_dump(mode="json"),
                )
            except asyncio.CancelledError:
                request.app.state.agent_metrics.append(
                    {"request_id": request.state.request_id, "status": "cancelled"}
                )
                raise
            except Exception as error:
                await emit(
                    "error",
                    {"code": error.code if isinstance(error, AgentError) else "AGENT_FAILED"},
                )
            finally:
                if not closed:
                    await queue.put(None)

        task = asyncio.create_task(execute())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            closed = True
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "private, no-store", "X-Accel-Buffering": "no"},
    )
