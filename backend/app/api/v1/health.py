from typing import Literal

from fastapi import APIRouter, Depends, Request, Response

from app.core.auth import bearer, require_operator_probe
from app.schemas.health import (
    Capabilities,
    HealthSummary,
    LivenessResponse,
    ReadinessResponse,
    WorkerState,
)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=LivenessResponse, summary="Process liveness độc lập hạ tầng")
async def live(request: Request) -> LivenessResponse:
    return LivenessResponse(service=request.app.state.settings.app_name)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    dependencies=[Depends(require_operator_probe)],
    responses={503: {"model": ReadinessResponse}},
    summary="Readiness hạ tầng, chưa bao gồm search encoder/index",
)
async def ready(request: Request, response: Response) -> ReadinessResponse:
    dependencies = await request.app.state.services.readiness()
    healthy = all(value == "healthy" for value in dependencies.values())
    if not healthy:
        response.status_code = 503
        request.state.error_category = "DEPENDENCY_UNAVAILABLE"
    return ReadinessResponse(status="ready" if healthy else "not_ready", dependencies=dependencies)


@router.get(
    "",
    response_model=HealthSummary,
    response_model_exclude_none=True,
    responses={503: {"model": HealthSummary}},
    summary="Health/capability summary",
)
async def summary(
    request: Request, response: Response, check: Literal["live", "ingest", "search"] = "live"
) -> HealthSummary:
    dependencies = None
    healthy = True
    runtime = getattr(request.app.state, "search_runtime", None)
    search_available = bool(runtime and runtime.available)
    if check != "live":
        # Dependency có điều kiện: public liveness, private readiness theo contract Phase 02.
        credentials = await bearer(request)
        await require_operator_probe(request, credentials)
        actual = await request.app.state.services.readiness()
        dependencies = {"metadata": actual["postgresql"], "objects": actual["minio"]}
        if check == "search":
            index_ready = False
            if search_available:
                try:
                    await runtime.registry.check()
                    index_ready = True
                except Exception:
                    pass
            dependencies.update(
                vectors=actual["qdrant"],
                encoder="healthy" if search_available else "not_initialized",
                index="healthy" if index_ready else "not_initialized",
            )
        healthy = all(value == "healthy" for value in dependencies.values())
    if not healthy:
        response.status_code = 503
        request.state.error_category = "NOT_READY"
    return HealthSummary(
        status="ok" if healthy else "not_ready",
        check=check,
        capabilities=Capabilities(
            text_search=search_available,
            image_search=search_available,
            multimodal=search_available and request.app.state.settings.multimodal_enabled,
            multi_intent=search_available and request.app.state.settings.multi_intent_enabled,
            rerank=search_available and request.app.state.settings.reranking_enabled,
            explanations=search_available and request.app.state.settings.rag_enabled,
            agent=request.app.state.settings.agent_enabled,
        ),
        worker=WorkerState(),
        dependencies=dependencies,
    )
