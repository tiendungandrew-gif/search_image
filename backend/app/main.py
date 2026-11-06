import logging
from collections import deque
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app import __version__
from app.api.router import router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.services.health import Services


def create_app(
    settings: Settings | None = None, services_factory: Callable[[Settings], Services] = Services
) -> FastAPI:
    try:
        settings = settings or get_settings()
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in exc.errors())
        raise RuntimeError(f"Cấu hình không hợp lệ ở fields: {fields}; xem docs/SETUP.md") from None
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        services = services_factory(settings)
        application.state.services = services
        runtime = None
        from app.services.rag.generator import Generator

        generator = Generator(settings)
        application.state.rag_generator = generator
        try:
            await services.initialize()
            if settings.search_enabled:
                from app.services.search.runtime import SearchRuntime

                runtime = SearchRuntime(services)
                application.state.search_runtime = runtime
                try:
                    await runtime.initialize()
                except Exception:
                    logging.getLogger("app.search").warning("search_initialization_failed")
            yield
        finally:
            await generator.close()
            if runtime is not None:
                await runtime.close()
            await services.close()

    application = FastAPI(
        title="AI Multimodal Image Search — Foundation",
        version=__version__,
        description=(
            "Prompt 08: semantic/multimodal retrieval và RAG metadata tùy chọn; "
            "semantic evidence có thể UNKNOWN; agents chưa triển khai."
        ),
        debug=False,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.search_runtime = None
    application.state.search_metrics = deque(maxlen=10000)
    application.state.rag_metrics = deque(maxlen=2000)
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
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
        allow_credentials=False,
    )
    application.add_middleware(
        RequestContextMiddleware,
        timeout=settings.request_timeout_seconds,
        cors_origins=settings.cors_origins,
        ingestion_timeout=settings.ingestion_timeout_seconds,
        rag_timeout=settings.rag_request_timeout_seconds,
    )
    return application
