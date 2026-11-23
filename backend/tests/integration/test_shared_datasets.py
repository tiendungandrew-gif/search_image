"""Opt-in shared libraries across real QA stores; synthetic vectors only."""

from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.auth import require_read_access
from app.db.models.access import AuditEvent, DatasetGrant, EntityDataset
from app.db.models.knowledge import Entity
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.rag.evidence_retriever import EvidenceRetriever
from tests.integration.test_access_control import PASSWORD, seed_search
from tests.integration.test_access_control import accounts as accounts

pytestmark = pytest.mark.integration


async def patch_library(admin, library, shared, **extra):
    return await admin.patch(
        f"/api/v1/admin/datasets/{library['id']}",
        json={"name": library["name"], "shared_with_members": shared, **extra},
    )


async def test_new_signup_reads_only_shared_images_search_and_evidence(accounts, qa_resources):
    app, admin, _, _, _ = accounts
    runtime, images = await seed_search(qa_resources, app)
    try:
        libraries = (await admin.get("/api/v1/admin/datasets")).json()["datasets"]
        assert all(not d["shared_with_members"] for d in libraries)
        common = next(d for d in libraries if d["key"] == "private_a")
        assert (await patch_library(admin, common, True)).status_code == 200
        # Older clients editing a name cannot silently undo the sharing decision.
        assert (
            await admin.patch(
                f"/api/v1/admin/datasets/{common['id']}", json={"name": common["name"]}
            )
        ).status_code == 200
        app.state.settings.agent_allow_fixture_knowledge = True
        async with qa_resources.services.database.sessions() as session, session.begin():
            for library in libraries:
                entity = Entity(
                    id=uuid4(),
                    canonical_name=library["key"],
                    name_key=library["key"],
                    entity_type="object",
                    provenance={"source_ref": "fixture://shared", "fixture": True},
                )
                session.add(entity)
                await session.flush()
                session.add(EntityDataset(dataset_id=UUID(library["id"]), entity_id=entity.id))

        @app.get("/qa/shared-evidence", dependencies=[Depends(require_read_access)])
        async def evidence_probe():
            evidence, _, _ = await EvidenceRetriever(runtime).retrieve(images)
            knowledge = KnowledgeRepository(qa_resources.services)
            return {
                "images": [str(e.image_id) for e in evidence],
                "common_entities": len((await knowledge.lookup("private_a")).entities),
                "private_entities": len((await knowledge.lookup("private_b")).entities),
            }

        origin = app.state.settings.cors_origins[0]
        async with AsyncClient(
            transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
        ) as member:
            assert (
                await member.post(
                    "/api/v1/auth/register",
                    json={
                        "username": "new_member",
                        "display_name": "New member",
                        "password": PASSWORD,
                    },
                )
            ).status_code == 201
            login = await member.post(
                "/api/v1/auth/login", json={"username": "new_member", "password": PASSWORD}
            )
            assert login.status_code == 200
            user = login.json()["user"]
            assert user["role"] == "user" and user["is_active"]
            assert [d["id"] for d in user["datasets"]] == [common["id"]]
            assert user["datasets"][0]["shared_with_members"] is True
            async with qa_resources.services.database.sessions() as session:
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(DatasetGrant)
                        .where(DatasetGrant.user_id == UUID(user["id"]))
                    )
                    == 0
                )
            member.headers["X-CSRF-Token"] = member.cookies["lens_csrf"]
            search = await member.post("/api/v1/search", json={"text": "a shape", "mode": "text"})
            assert search.status_code == 200, search.text
            assert [r["image_id"] for r in search.json()["results"]] == [str(images[0])]
            filtered = await member.post(
                "/api/v1/search",
                json={
                    "text": "a shape",
                    "mode": "text",
                    "filters": {"source_dataset": "private_b"},
                },
            )
            assert filtered.status_code == 200 and filtered.json()["total_results"] == 0
            assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 200
            assert (await member.get(f"/api/v1/images/{images[1]}/content")).status_code == 404
            assert (await member.get("/qa/shared-evidence")).json() == {
                "images": [str(images[0])],
                "common_entities": 1,
                "private_entities": 0,
            }
            assert (await member.get("/api/v1/admin/datasets")).status_code == 403
            assert (
                await member.patch(f"/api/v1/admin/images/{images[0]}", json={})
            ).status_code == 403
            assert (
                await member.post(f"/api/v1/admin/users/{user['id']}/sessions/revoke")
            ).status_code == 403
            async with AsyncClient(transport=ASGITransport(app), base_url=origin) as anonymous:
                assert (
                    await anonymous.get(f"/api/v1/images/{images[0]}/content")
                ).status_code == 404
    finally:
        await runtime.close()


async def test_shared_access_changes_without_relogin_and_preserves_explicit_grants(
    accounts, qa_resources
):
    app, admin, member, _, uid = accounts
    runtime, images = await seed_search(qa_resources, app)
    try:
        common = next(
            d
            for d in (await admin.get("/api/v1/admin/datasets")).json()["datasets"]
            if d["key"] == "private_a"
        )
        assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
        assert (await patch_library(admin, common, True)).status_code == 200
        assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 200
        # Explicit grant + common access still produces one dataset.
        assert (
            await admin.put(
                f"/api/v1/admin/users/{uid}/datasets", json={"dataset_ids": [common["id"]]}
            )
        ).status_code == 200
        assert len((await member.get("/api/v1/auth/me")).json()["user"]["datasets"]) == 1
        assert (await patch_library(admin, common, False)).status_code == 200
        assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 200
        assert (
            await admin.put(f"/api/v1/admin/users/{uid}/datasets", json={"dataset_ids": []})
        ).status_code == 200
        assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
        assert (await patch_library(admin, common, True)).status_code == 200
        assert (await patch_library(admin, common, True, is_active=False)).status_code == 200
        assert (await member.get(f"/api/v1/images/{images[0]}/content")).status_code == 404
        assert (await member.get("/api/v1/auth/me")).json()["user"]["datasets"] == []
        # Sharing changes remain Admin-only and session-bound CSRF protected.
        assert (await patch_library(member, common, True)).status_code == 403
        assert (
            await admin.patch(
                f"/api/v1/admin/datasets/{common['id']}",
                json={"name": common["name"], "shared_with_members": True},
                headers={"X-CSRF-Token": "wrong"},
            )
        ).status_code == 403
        assert any(
            e["details"].get("shared_with_members") is True
            for e in (await admin.get("/api/v1/admin/audit")).json()["events"]
        )
    finally:
        await runtime.close()


async def test_admin_revokes_all_user_sessions_without_changing_password(accounts, qa_resources):
    app, admin, member, _, uid = accounts
    origin = app.state.settings.cors_origins[0]
    async with AsyncClient(
        transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
    ) as second:
        assert (
            await second.post(
                "/api/v1/auth/login", json={"username": "reader", "password": PASSWORD}
            )
        ).status_code == 200
        assert (await member.post(f"/api/v1/admin/users/{uid}/sessions/revoke")).status_code == 403
        assert (await admin.post(f"/api/v1/admin/users/{uid}/sessions/revoke")).status_code == 200
        for client in [member, second]:
            assert (await client.get("/api/v1/auth/me")).json()["user"] is None
            assert (await client.get("/api/v1/system/workspace")).status_code == 401
        assert (
            await second.post(
                "/api/v1/auth/login", json={"username": "reader", "password": PASSWORD}
            )
        ).status_code == 200
        async with qa_resources.services.database.sessions() as session:
            assert (
                await session.scalar(
                    select(AuditEvent.resource_id).where(
                        AuditEvent.action == "user.sessions_revoked"
                    )
                )
                == uid
            )
