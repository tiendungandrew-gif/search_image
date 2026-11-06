from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def client_for(app):
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_write_token_required_and_read_token_cannot_mutate(app, settings, auth_headers):
    settings.write_api_token = __import__("pydantic").SecretStr(
        "unit-write-token-that-is-long-enough"
    )
    async with client_for(app) as client:
        denied = await client.post("/api/v1/images", headers=auth_headers)
        assert denied.status_code == 403
        good = {"Authorization": "Bearer " + settings.write_api_token.get_secret_value()}
        missing = await client.post("/api/v1/images", headers=good)
        assert (
            missing.status_code == 400
            and missing.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
        )
        assert (await client.get("/api/v1/system/info", headers=good)).status_code == 200


async def test_upload_metadata_and_request_body_limits(app, settings):
    settings.write_api_token = __import__("pydantic").SecretStr(
        "unit-write-token-that-is-long-enough"
    )
    headers = {
        "Authorization": "Bearer " + settings.write_api_token.get_secret_value(),
        "Idempotency-Key": "test-key",
    }
    async with client_for(app) as client:
        response = await client.post(
            "/api/v1/images",
            headers=headers,
            files={"image": ("not-a-path.png", b"bad", "image/png")},
            data={"metadata": '{"source_dataset":"unknown"}'},
        )
        assert response.status_code == 422
        response = await client.post("/api/v1/index/jobs", headers=headers, content=b" " * 65537)
        assert response.status_code == 413
        schema = (await client.get("/openapi.json")).json()
        assert (
            "multipart/form-data"
            in schema["paths"]["/api/v1/images"]["post"]["requestBody"]["content"]
        )
        assert "/api/v1/search" in schema["paths"]


@pytest.mark.parametrize(
    "metadata",
    [
        "not json",
        "[]",
        '{"source_dataset":"fixture","license":"CC0","rights_ref":"ok","status":"ready"}',
    ],
)
async def test_unknown_or_malformed_metadata_rejected(app, settings, metadata):
    settings.write_api_token = __import__("pydantic").SecretStr(
        "unit-write-token-that-is-long-enough"
    )
    async with client_for(app) as client:
        response = await client.post(
            "/api/v1/images",
            headers={
                "Authorization": "Bearer " + settings.write_api_token.get_secret_value(),
                "Idempotency-Key": "metadata-key",
            },
            files={"image": ("fake.png", b"bad", "image/png")},
            data={"metadata": metadata},
        )
        assert response.status_code == 422
