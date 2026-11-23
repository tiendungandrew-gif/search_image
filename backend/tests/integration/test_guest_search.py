"""Public opt-in/revocation across real PG/Qdrant/MinIO; synthetic query vectors."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.db.models.access import LoginThrottle
from tests.integration.test_access_control import accounts as accounts
from tests.integration.test_access_control import seed_search

pytestmark = pytest.mark.integration


async def test_guest_public_scope_never_inherits_member_sharing(accounts, qa_resources):
    app, admin, member, _, _ = accounts
    runtime, images = await seed_search(qa_resources, app)
    app.state.settings.guest_search_enabled = True
    origin = app.state.settings.cors_origins[0]
    try:
        libraries = (await admin.get("/api/v1/admin/datasets")).json()["datasets"]
        a = next(d for d in libraries if d["key"] == "private_a")
        assert not a["is_public"]

        async def visibility(**flags):
            response = await admin.patch(
                f"/api/v1/admin/datasets/{a['id']}", json={"name": a["name"], **flags}
            )
            assert response.status_code == 200, response.text

        async with AsyncClient(
            transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
        ) as guest:
            await visibility(shared_with_members=True)
            assert (await guest.post("/api/v1/search", json={"text": "a shape"})).json()[
                "results"
            ] == []
            assert (await guest.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
            assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 200
            await visibility(is_public=True)
            # Older clients may edit a name without undoing the public flag.
            await visibility()
            snapshot = (await guest.get("/api/v1/public/workspace")).json()
            assert snapshot["dataset"]["images"] == 1
            assert [d["key"] for d in snapshot["public_datasets"]] == ["private_a"]
            assert snapshot["capabilities"]["text_search"]
            assert not snapshot["capabilities"]["image_search"]
            search = await guest.post("/api/v1/search", json={"text": "con meo"})
            assert search.status_code == 200, search.text
            assert [r["image_id"] for r in search.json()["results"]] == [str(images[0])]
            content = await guest.get(search.json()["results"][0]["image_url"])
            assert (
                content.status_code == 200
                and content.headers["cache-control"] == "private, no-store"
            )
            assert (await guest.get(f"/api/v1/images/{images[0]}")).json()["indexing"] == []
            for suffix in ["", "/content?variant=original", "/content?variant=thumbnail"]:
                assert (await guest.get(f"/api/v1/images/{images[1]}{suffix}")).status_code == 404
            filtered = await guest.post(
                "/api/v1/search",
                json={"text": "a shape", "filters": {"source_dataset": "private_b"}},
            )
            assert filtered.status_code == 200 and filtered.json()["results"] == []
            for path in [
                "/admin/users",
                "/system/workspace",
                "/system/evaluation",
                "/rag/status",
                "/search/agent/status",
            ]:
                assert (await guest.get("/api/v1" + path)).status_code == 401
            assert (await guest.post("/api/v1/images", json={})).status_code == 401
            await visibility(is_public=False)
            assert (await guest.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
            assert (await guest.post("/api/v1/search", json={"text": "a shape"})).json()[
                "results"
            ] == []
            assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 200
            await visibility(is_public=True, is_active=False)
            assert (await guest.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
            assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
    finally:
        await runtime.close()


async def test_guest_throttle_origin_and_login_gates(accounts, qa_resources):
    app, admin, _, _, _ = accounts
    runtime, _ = await seed_search(qa_resources, app)
    app.state.settings.guest_search_enabled = True
    app.state.settings.guest_search_per_minute = 2
    origin = app.state.settings.cors_origins[0]
    try:
        async with AsyncClient(
            transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
        ) as guest:
            for _ in range(2):
                assert (
                    await guest.post("/api/v1/search", json={"text": "a shape"})
                ).status_code == 200
            denied = await guest.post(
                "/api/v1/search",
                json={"text": "a shape"},
                headers={"X-Forwarded-For": "198.51.100.8"},
            )
            assert (
                denied.status_code == 429 and denied.json()["error"]["code"] == "GUEST_RATE_LIMITED"
            )
            async with qa_resources.services.database.sessions() as session, session.begin():
                await session.execute(update(LoginThrottle).values(bucket="2000-01-01T00:00"))
            assert (await guest.post("/api/v1/search", json={"text": "a shape"})).status_code == 200
            assert (
                await guest.post(
                    "/api/v1/search",
                    json={"text": "a shape"},
                    headers={"Origin": "https://evil.example"},
                )
            ).status_code == 403
            assert (
                await guest.post(
                    "/api/v1/search",
                    json={"text": "a shape"},
                    headers={"Authorization": "Bearer invalid"},
                )
            ).status_code == 401
            for body in [
                {"text": "a shape", "image_id": "00000000-0000-4000-8000-000000000001"},
                {"text": "a shape", "rerank": True},
                {"text": "a shape", "mode": "agent"},
            ]:
                assert (await guest.post("/api/v1/search", json=body)).status_code == 401
            assert (
                await guest.post("/api/v1/search", json={"text": "a shape", "top_k": 51})
            ).status_code == 422
            assert (
                await guest.post(
                    "/api/v1/search/multimodal",
                    files={"image": ("test.png", b"invalid", "image/png")},
                )
            ).status_code == 401
            app.state.settings.guest_search_enabled = False
            assert (await guest.get("/api/v1/public/workspace")).status_code == 401
    finally:
        await runtime.close()
