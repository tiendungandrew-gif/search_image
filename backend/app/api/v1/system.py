from fastapi import APIRouter, Depends, Request

from app import __version__
from app.core.auth import require_read_access
from app.schemas.health import SystemInfo

router = APIRouter(prefix="/system", tags=["System"], dependencies=[Depends(require_read_access)])


@router.get("/info", response_model=SystemInfo, summary="Thông tin ứng dụng an toàn")
async def system_info(request: Request) -> SystemInfo:
    settings = request.app.state.settings
    return SystemInfo(
        app_name=settings.app_name, app_version=__version__, environment=settings.app_env
    )


@router.get("/search-runtime", summary="Private research profiling; no credentials or query data")
async def search_runtime(request: Request):
    import asyncio
    import os
    import platform
    import resource
    from pathlib import Path

    runtime = getattr(request.app.state, "search_runtime", None)
    settings = request.app.state.settings
    usage = resource.getrusage(resource.RUSAGE_SELF)
    memory = {}
    for line in (await asyncio.to_thread(Path("/proc/self/status").read_text)).splitlines():
        key = line.split(":", 1)[0]
        if key in {"VmRSS", "VmHWM", "Threads"}:
            memory[key] = int(line.split()[1])
    info = {
        "status": "ready" if runtime and runtime.available else "not_ready",
        "pid": os.getpid(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "cpu_user_seconds": usage.ru_utime,
        "cpu_system_seconds": usage.ru_stime,
        "process_memory_kib": {key: value for key, value in memory.items() if key != "Threads"},
        "process_threads": memory.get("Threads"),
        "model_initialization_ms": getattr(runtime, "initialization_ms", None),
        "settings": {
            key: getattr(settings, key)
            for key in [
                "embedding_cpu_threads",
                "embedding_device",
                "search_max_top_k",
                "search_default_candidates",
                "search_queue_capacity",
                "search_queue_wait_seconds",
                "search_object_check_concurrency",
                "reranking_max_candidates",
                "reranking_timeout_ms",
            ]
        },
        "gpu_measurements": None,
    }
    if runtime and runtime.available:
        info["model"] = {
            "model_id": str(runtime.registry.model.id),
            "name": runtime.registry.model.model_name,
            "revision": runtime.registry.model.model_revision,
            "manifest_sha256": runtime.registry.model.manifest_sha256,
            "dimension": runtime.registry.model.dimension,
            "device": runtime.encoder.device,
            "index_id": str(runtime.registry.index.id),
            "collection": runtime.registry.index.collection_name,
            "generation": runtime.registry.generation,
        }
    return info
