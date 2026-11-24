import asyncio
import logging
from collections import deque
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app import __version__
from app.api.router import router
from app.core.access import AccessContextMiddleware
from app.core.config import Settings, get_settings
from app.core.container import Services
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app(
    settings: Settings | None = None, services_factory: Callable[[Settings], Services] = Services
) -> FastAPI:
    try:
        settings = settings or get_settings()
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in exc.errors())
        raise RuntimeError(
            f"Cấu hình không hợp lệ ở fields: {fields}; xem docs/operations/SETUP.md"
        ) from None
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with AsyncExitStack() as resources:
            services = services_factory(settings)
            resources.push_async_callback(services.close)
            application.state.services = services
            from app.services.rag.generator import Generator

            generator = Generator(settings)
            resources.push_async_callback(generator.close)
            application.state.rag_generator = generator
            runtime = None
            if settings.search_enabled:
                from app.services.search.runtime import SearchRuntime

                runtime = SearchRuntime(services)
                resources.push_async_callback(runtime.close)
                application.state.search_runtime = runtime
                try:
                    await runtime.initialize()
                except Exception:
                    logging.getLogger("app.search").warning("search_initialization_failed")
            if settings.agent_enabled:
                from app.services.agent.agent_service import AgentService

                agent = AgentService(services, runtime, generator)
                resources.push_async_callback(agent.close)
                application.state.agent_service = agent
            yield

    application = FastAPI(
        title="AI Multimodal Image Search — Foundation",
        version=__version__,
        description=(
            "Phase 09: Semantic Search, RAG và bounded Agent Search tùy chọn; "
            "quan hệ cần evidence trong database, không dùng kiến thức model thay dữ liệu."
        ),
        debug=False,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.password_slots = asyncio.Semaphore(2)
    application.state.search_runtime = None
    application.state.search_metrics = deque(maxlen=10000)
    application.state.rag_metrics = deque(maxlen=2000)
    application.state.agent_service = None
    application.state.agent_metrics = deque(maxlen=2000)
    application.state.agent_http_metrics = deque(maxlen=10000)
    # Manual JSON/multipart parser: register schema để OpenAPI requestBody $ref có đích.
    from app.schemas.search import SearchRequest

    application.openapi_schema = None
    application.include_router(router, prefix=settings.api_prefix)
    original_openapi = application.openapi

    def openapi():
        schema = original_openapi()
        definition = SearchRequest.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = definition.pop("$defs", {})
        schema.setdefault("components", {}).setdefault("schemas", {}).update(definitions)
        schema["components"]["schemas"]["SearchRequest"] = definition
        return schema

    application.openapi = openapi
    register_exception_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Idempotency-Key",
            "X-CSRF-Token",
        ],
        expose_headers=["X-Request-ID"],
        allow_credentials=True,
    )
    application.add_middleware(
        RequestContextMiddleware,
        timeout=settings.request_timeout_seconds,
        cors_origins=settings.cors_origins,
        ingestion_timeout=settings.ingestion_timeout_seconds,
        rag_timeout=settings.rag_request_timeout_seconds,
        agent_timeout=settings.agent_timeout_seconds + 1,
    )
    application.add_middleware(AccessContextMiddleware)
    return application
