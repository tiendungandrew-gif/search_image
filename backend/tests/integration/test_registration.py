"""Public signup on disposable QA databases; no serving accounts are created."""

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.passwords import verify_password
from app.db.models.access import AuditEvent, DatasetGrant, User
from app.main import create_app

pytestmark = pytest.mark.integration
PASSWORD = "Registration-test-only-2026!"


@pytest.fixture
async def signup(qa_resources):
    cfg = qa_resources.settings
    cfg.auth_legacy_tokens_enabled = False
    app = create_app(cfg)
    app.state.services = qa_resources.services
    origin = cfg.cors_origins[0]
    async with AsyncClient(
        transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
    ) as client:
        yield app, client


def body(username="New_Reader"):
    return {"username": username, "display_name": "  Người dùng mới  ", "password": PASSWORD}


async def test_signup_login_logout_and_least_privilege(signup):
    app, client = signup
    result = await client.post("/api/v1/auth/register", json=body())
    assert result.status_code == 201, result.text
    assert result.json() == {"status": "registered"}
    assert result.headers["cache-control"] == "no-store"
    assert not result.headers.get_list("set-cookie")
    assert (await client.get("/api/v1/auth/me")).json()["user"] is None
    result = await client.post(
        "/api/v1/auth/login", json={"username": "NEW_READER", "password": PASSWORD}
    )
    assert result.status_code == 200, result.text
    account = result.json()["user"]
    assert account["username"] == "new_reader"
    assert account["display_name"] == "Người dùng mới"
    assert account["role"] == "user" and account["is_active"] and not account["is_demo"]
    assert account["datasets"] == []
    assert PASSWORD not in result.text and "password_hash" not in result.text
    assert "HttpOnly" in result.headers.get_list("set-cookie")[0]
    assert (await client.get("/api/v1/admin/users")).status_code == 403
    assert (await client.get(f"/api/v1/images/{uuid4()}/content")).status_code == 404
    async with app.state.services.database.sessions() as session:
        user = await session.scalar(select(User).where(User.username == "new_reader"))
        assert user.password_hash != PASSWORD and verify_password(PASSWORD, user.password_hash)
        assert await session.scalar(select(func.count()).select_from(DatasetGrant)) == 0
        assert await session.scalar(
            select(AuditEvent.resource_id).where(AuditEvent.action == "auth.registered")
        ) == str(user.id)
    client.headers["X-CSRF-Token"] = client.cookies["lens_csrf"]
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert (await client.get("/api/v1/auth/me")).json()["user"] is None


async def test_signup_duplicate_race_and_normalization(signup):
    app, client = signup
    results = await asyncio.gather(
        client.post("/api/v1/auth/register", json=body("RaceReader")),
        client.post("/api/v1/auth/register", json=body("racereader")),
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    rejected = next(r for r in results if r.status_code == 409)
    assert rejected.json()["error"]["code"] == "USERNAME_TAKEN"
    async with app.state.services.database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_signup_validation_origin_reserved_names_and_throttle(signup):
    app, client = signup
    for extra in [
        {"role": "admin"},
        {"is_demo": True},
        {"dataset_ids": [str(uuid4())]},
        {"password": "short"},
        {"display_name": "   "},
        {"display_name": "name\ncontrol"},
        {"username": "a b"},
    ]:
        assert (await client.post("/api/v1/auth/register", json=body() | extra)).status_code == 422
    for headers in [{"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}]:
        assert (
            await client.post("/api/v1/auth/register", json=body(), headers=headers)
        ).status_code == 403
    for username in ["demo_admin", "DEMO_USER"]:
        assert (await client.post("/api/v1/auth/register", json=body(username))).status_code == 409
    app.state.settings.auth_login_attempts_per_minute = 3
    for status in [201, 409, 409, 429]:
        result = await client.post("/api/v1/auth/register", json=body("throttled_reader"))
        assert result.status_code == status, result.text
