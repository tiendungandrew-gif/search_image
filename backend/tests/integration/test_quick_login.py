"""Real database sessions, provisioned demo accounts and ordinary RBAC after quick login."""

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.cli.quick_login import provision
from app.core.passwords import hash_password
from app.db.models.access import AccessDataset, AuthSession, DatasetGrant, User
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def quick_app(qa_resources):
    cfg = qa_resources.settings
    cfg.auth_quick_login_enabled = True
    cfg.auth_legacy_tokens_enabled = False
    cfg.request_timeout_seconds = 30
    app = create_app(cfg)
    app.state.services = qa_resources.services
    password = "QA-real-admin-password"
    encoded = await asyncio.to_thread(hash_password, password)
    async with qa_resources.services.database.sessions() as session, session.begin():
        real = User(
            username="real_admin", display_name="Real Admin", role="admin", password_hash=encoded
        )
        library = AccessDataset(id=uuid4(), key="quick_private", name="Quick library")
        session.add_all([real, library])
        await session.flush()
    await provision(qa_resources.services, enable=True)
    async with AsyncClient(transport=ASGITransport(app), base_url=cfg.cors_origins[0]) as client:
        client.headers["Origin"] = cfg.cors_origins[0]
        yield app, client, real.id, library.id


async def test_quick_roles_sessions_privileges_csrf_and_disable(quick_app, qa_resources):
    app, client, real_id, library_id = quick_app
    snapshot = (await client.get("/api/v1/auth/me")).json()
    assert snapshot["user"] is None and snapshot["quick_login_roles"] == ["admin", "user"]
    rejected = await client.post(
        "/api/v1/auth/quick-login",
        json={"role": "admin"},
        headers={"Origin": "https://evil.example"},
    )
    assert rejected.status_code == 403
    for role in ["admin", "user"]:
        response = await client.post("/api/v1/auth/quick-login", json={"role": role})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["user"]["role"] == role and body["user"]["is_demo"] is True
        assert "password" not in response.text and "scrypt" not in response.text
        assert "HttpOnly" in response.headers.get_list("set-cookie")[0]
        client.headers["X-CSRF-Token"] = client.cookies["lens_csrf"]
        admin = await client.get("/api/v1/admin/users")
        assert admin.status_code == (200 if role == "admin" else 403)
        assert (
            await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"})
        ).status_code == 403
        if role == "admin":
            assert (
                await client.patch(f"/api/v1/admin/users/{real_id}", json={"is_active": False})
            ).json()["error"]["code"] == "LAST_ADMIN"
            assert (
                await client.patch(
                    f"/api/v1/admin/users/{body['user']['id']}", json={"role": "user"}
                )
            ).json()["error"]["code"] == "DEMO_ROLE_FIXED"
        else:
            assert [d["id"] for d in body["user"]["datasets"]] == [str(library_id)]
            for method, path in [
                ("POST", "/admin/images/upload"),
                ("POST", "/admin/indexes/activate"),
                ("PUT", f"/admin/users/{body['user']['id']}/datasets"),
            ]:
                assert (await client.request(method, "/api/v1" + path, json={})).status_code == 403
        if role == "admin":
            assert (await client.post("/api/v1/auth/logout")).status_code == 200
            assert (await client.get("/api/v1/auth/me")).json()["user"] is None
    regular = await client.post(
        "/api/v1/auth/login", json={"username": "real_admin", "password": "QA-real-admin-password"}
    )
    assert regular.status_code == 200 and regular.json()["user"]["is_demo"] is False
    await client.post("/api/v1/auth/quick-login", json={"role": "user"})
    saved = client.cookies["lens_session"]
    app.state.settings.auth_quick_login_enabled = False
    assert (await client.get("/api/v1/system/workspace")).status_code == 401
    assert (
        await client.post("/api/v1/auth/quick-login", json={"role": "admin"})
    ).status_code == 404
    assert (await client.get("/api/v1/auth/me")).json()["quick_login_roles"] == []
    # Even an invalid programmatic configuration must not open quick login in production.
    app.state.settings.auth_quick_login_enabled = True
    app.state.settings.app_env = "production"
    client.cookies.set("lens_session", saved)
    assert (await client.get("/api/v1/system/workspace")).status_code == 401
    assert (
        await client.post("/api/v1/auth/quick-login", json={"role": "admin"})
    ).status_code == 404


async def test_quick_accounts_missing_locked_revoked_and_grants_preserved(quick_app, qa_resources):
    app, client, _, library_id = quick_app
    services = qa_resources.services
    async with services.database.sessions() as session, session.begin():
        reader = await session.scalar(select(User).where(User.username == "demo_user"))
        reader.is_active = False
    assert (await client.post("/api/v1/auth/quick-login", json={"role": "user"})).status_code == 409
    assert (await client.get("/api/v1/auth/me")).json()["quick_login_roles"] == ["admin"]
    await provision(services, enable=True)
    response = await client.post("/api/v1/auth/quick-login", json={"role": "user"})
    assert response.status_code == 200
    async with services.database.sessions() as session, session.begin():
        grant = await session.get(DatasetGrant, (reader.id, library_id))
        await session.delete(grant)
    assert (await client.get("/api/v1/auth/me")).json()["user"]["datasets"] == []
    await provision(services, enable=True)
    assert (await client.post("/api/v1/auth/quick-login", json={"role": "user"})).json()["user"][
        "datasets"
    ] == []
    await provision(services, enable=False)
    assert (await client.get("/api/v1/system/workspace")).status_code == 401
    async with services.database.sessions() as session:
        assert (await session.scalars(select(AuthSession))).all() == []
    assert (await client.get("/api/v1/auth/me")).json()["quick_login_roles"] == []


async def test_setup_does_not_take_over_regular_username_and_rate_limit(quick_app, qa_resources):
    app, client, _, _ = quick_app
    app.state.settings.auth_login_attempts_per_minute = 3
    for _ in range(3):
        assert (
            await client.post("/api/v1/auth/quick-login", json={"role": "admin"})
        ).status_code == 200
    assert (
        await client.post("/api/v1/auth/quick-login", json={"role": "admin"})
    ).status_code == 429
    async with qa_resources.services.database.sessions() as session, session.begin():
        demo = await session.scalar(select(User).where(User.username == "demo_user"))
        demo.is_demo = False  # Simulate a reserved-name conflict; provisioning must refuse it.
    with pytest.raises(ValueError, match="DEMO_USERNAME_CONFLICT"):
        await provision(qa_resources.services, enable=True)
