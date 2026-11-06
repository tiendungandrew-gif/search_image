import asyncio
import json
import logging
from contextlib import asynccontextmanager
from io import StringIO
from uuid import UUID, uuid4

from fastapi import Query
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError
from app.core.logging import JSONFormatter
from app.main import create_app


@asynccontextmanager
async def async_client(app):
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_liveness_never_probes_dependencies(app, fake_services):
    fake_services.readiness.side_effect = RuntimeError("offline")
    async with async_client(app) as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    fake_services.readiness.assert_not_awaited()
    fake_services.close.assert_awaited_once()


async def test_health_summary_has_no_fake_search_capability(app, fake_services):
    async with async_client(app) as client:
        result = (await client.get("/api/v1/health")).json()
        assert (await client.get("/api/v1/search")).status_code == 405
        assert (await client.post("/api/v1/search", json={"text": "test"})).status_code == 401
        schema = (await client.get("/openapi.json")).json()
        assert "/api/v1/search" in schema["paths"]
        assert (await client.get("/docs")).status_code == 200
    assert result["status"] == "ok"
    assert not any(result["capabilities"].values())
    fake_services.readiness.assert_not_awaited()


async def test_readiness_authenticated_and_real_status_aggregation(
    app, auth_headers, fake_services
):
    async with async_client(app) as client:
        assert (await client.get("/api/v1/health/ready")).status_code == 401
        assert (await client.get("/api/v1/health/ready", headers=auth_headers)).json()[
            "status"
        ] == "ready"
        fake_services.readiness.return_value["qdrant"] = "timeout"
        response = await client.get("/api/v1/health/ready", headers=auth_headers)
        assert response.status_code == 503
        assert response.json()["dependencies"]["qdrant"] == "timeout"
        assert (
            await client.get("/api/v1/health?check=ingest", headers=auth_headers)
        ).status_code == 200
        search = await client.get("/api/v1/health?check=search", headers=auth_headers)
        assert search.status_code == 503
        assert search.json()["dependencies"]["encoder"] == "not_initialized"


async def test_system_info_safe_and_protected(app, auth_headers, settings):
    async with async_client(app) as client:
        assert (await client.get("/api/v1/system/info")).status_code == 401
        response = await client.get("/api/v1/system/info", headers=auth_headers)
    assert response.status_code == 200
    assert set(response.json()) == {"app_name", "app_version", "environment", "api_version"}
    assert settings.api_token.get_secret_value() not in response.text


async def test_request_id_validated_and_errors_share_envelope(app):
    supplied = str(uuid4())
    async with async_client(app) as client:
        response = await client.get(
            "/api/v1/health?check=invalid", headers={"X-Request-ID": supplied}
        )
        assert response.status_code == 422
        assert response.headers["x-request-id"] == supplied
        assert response.json()["error"]["request_id"] == supplied
        assert "input" not in response.text
        generated = await client.get("/missing", headers={"X-Request-ID": "bad\tvalue"})
        assert (
            str(UUID(generated.headers["x-request-id"])) == generated.json()["error"]["request_id"]
        )


async def test_safe_exceptions_and_database_outage(app):

    @app.get("/test/error")
    async def failing():
        raise RuntimeError("PRIVATE_CONNECTION_PASSWORD")

    @app.get("/test/database")
    async def database():
        raise SQLAlchemyError("PRIVATE_DATABASE_URL")

    @app.get("/test/service")
    async def service():
        raise AppError(
            503, "DEPENDENCY_UNAVAILABLE", "Dịch vụ tạm thời không khả dụng", retryable=True
        )

    async with async_client(app) as client:
        assert (await client.get("/test/database")).status_code == 503
        assert (await client.get("/test/service")).json()["error"]["retryable"] is True
        response = await client.get("/test/error")
    assert response.status_code == 500
    assert "PRIVATE_" not in response.text


async def test_request_timeout_before_headers(settings, fake_services):
    settings.request_timeout_seconds = 0.05
    settings.dependency_timeout_seconds = 0.02
    app = create_app(settings, lambda _: fake_services)

    @app.get("/test/slow")
    async def slow():
        await asyncio.sleep(0.5)
        return {"status": "late"}

    async with async_client(app) as client:
        response = await client.get("/test/slow", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "DEADLINE_EXCEEDED"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_structured_logs_redact_query_headers_and_sdk_exception(app, settings):
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger = logging.getLogger("app.access")
    logger.addHandler(handler)

    @app.get("/test/log")
    async def endpoint(text: str = Query()):
        return {"ok": True}

    try:
        async with async_client(app) as client:
            response = await client.get(
                "/test/log?text=PRIVATE_QUERY",
                headers={"Authorization": f"Bearer {settings.api_token.get_secret_value()}"},
            )
    finally:
        logger.removeHandler(handler)
    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["status_code"] == 200
    assert event["path"] == "/test/log"
    assert event["duration_ms"] >= 0
    assert event["request_id"] == response.headers["x-request-id"]
    assert "PRIVATE_QUERY" not in stream.getvalue()
    assert settings.api_token.get_secret_value() not in stream.getvalue()


async def test_cors_is_restricted(app):
    async with async_client(app) as client:
        allowed = await client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        denied = await client.options(
            "/api/v1/health",
            headers={"Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "GET"},
        )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
