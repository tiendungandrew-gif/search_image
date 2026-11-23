"""Real disposable PG/Qdrant/MinIO account and isolation checks; vectors are synthetic."""

import asyncio
from datetime import timedelta
from uuid import UUID

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.access import Principal, current_principal
from app.core.passwords import hash_password
from app.db.models.access import AuthSession, User
from app.db.models.indexing import ActiveSearchIndex
from app.main import create_app
from app.schemas.filters import Filters
from app.schemas.ingestion import ImageMetadataInput
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, now
from app.services.indexing.worker import Worker
from app.services.rag.evidence_retriever import EvidenceRetriever
from app.services.search.registry import SearchRegistry
from app.services.search.runtime import SearchRuntime
from app.services.search.vector_retriever import VectorRetriever
from tests.fixtures.synthetic import SyntheticEncoder, image_bytes

pytestmark = pytest.mark.integration
PASSWORD = "QA-only-password-2026"


@pytest.fixture
async def accounts(qa_resources):
    cfg = qa_resources.settings
    cfg.auth_legacy_tokens_enabled = False
    cfg.request_timeout_seconds = 30
    app = create_app(cfg)
    app.state.services = qa_resources.services
    encoded = await asyncio.to_thread(hash_password, PASSWORD)
    async with qa_resources.services.database.sessions() as session, session.begin():
        admin = User(username="admin", display_name="QA Admin", role="admin", password_hash=encoded)
        user = User(username="reader", display_name="QA Reader", role="user", password_hash=encoded)
        session.add_all([admin, user])
        await session.flush()
    origin = cfg.cors_origins[0]
    async with (
        AsyncClient(transport=ASGITransport(app), base_url=origin) as admin_client,
        AsyncClient(transport=ASGITransport(app), base_url=origin) as user_client,
    ):
        for client, username in [(admin_client, "admin"), (user_client, "reader")]:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": PASSWORD},
                headers={"Origin": origin},
            )
            assert response.status_code == 200, response.text
            client.headers.update({"Origin": origin, "X-CSRF-Token": client.cookies["lens_csrf"]})
        yield app, admin_client, user_client, str(admin.id), str(user.id)


async def test_account_sessions_csrf_last_admin_and_revocation(accounts):
    app, admin, user, aid, uid = accounts
    for path in [
        "/admin/users",
        "/admin/datasets",
        "/admin/images",
        "/admin/indexes",
        "/admin/audit",
        "/system/evaluation",
        "/rag/status",
        "/search/agent/status",
    ]:
        response = await user.get("/api/v1" + path)
        assert response.status_code == 403, (path, response.text)
    assert (await admin.patch(f"/api/v1/admin/users/{aid}", json={"role": "user"})).json()["error"][
        "code"
    ] == "LAST_ADMIN"
    assert (
        await admin.patch(f"/api/v1/admin/users/{aid}", json={"is_active": False})
    ).status_code == 409
    assert (
        await user.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403
    assert (
        await user.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})
    ).status_code == 403
    assert (await user.get("/api/v1/auth/me")).json()["user"]["role"] == "user"
    snapshot = await admin.get("/api/v1/admin/users")
    assert "scrypt" not in snapshot.text and PASSWORD not in snapshot.text
    # Header token does not bypass disabled compatibility, even with a valid session cookie.
    assert (
        await user.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer " + app.state.settings.api_token.get_secret_value()},
        )
    ).status_code == 401
    assert (
        await user.get(
            "/api/v1/health/ready",
            headers={"Authorization": "Bearer " + app.state.settings.api_token.get_secret_value()},
        )
    ).status_code == 200
    saved = user.cookies["lens_session"]
    assert (
        await admin.post(
            f"/api/v1/admin/users/{uid}/password", json={"password": "New-QA-only-password!"}
        )
    ).status_code == 200
    assert (await user.get("/api/v1/system/workspace")).status_code == 401
    result = await user.post(
        "/api/v1/auth/login", json={"username": "reader", "password": "New-QA-only-password!"}
    )
    assert result.status_code == 200
    cookie = result.headers.get_list("set-cookie")[0]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    user.headers["X-CSRF-Token"] = user.cookies["lens_csrf"]
    for current, expected in [("wrong-password", 403), ("New-QA-only-password!", 422)]:
        rejected = await user.post(
            "/api/v1/auth/password",
            json={"current_password": current, "password": "New-QA-only-password!"},
        )
        assert rejected.status_code == expected, rejected.text
    assert (
        await user.post(
            "/api/v1/auth/password",
            json={
                "current_password": "New-QA-only-password!",
                "password": "Next-QA-only-password!",
            },
        )
    ).status_code == 200
    user.cookies.set("lens_session", saved)
    assert (await user.get("/api/v1/auth/me")).json()["user"] is None
    assert (await admin.get("/api/v1/admin/audit")).status_code == 200


async def seed_search(resources, app, titles=None, captions=None):
    services = resources.services
    encoder = SyntheticEncoder()
    encoder.encode_text = lambda values: np.ones((len(values), 8), dtype=np.float32)
    index, _ = await resources.index(encoder)
    images = []
    for n, dataset in enumerate(["private_a", "private_b"]):
        _, body = await ingest(
            services,
            image_bytes(n),
            ImageMetadataInput(
                source_dataset=dataset,
                title=titles[n] if titles else dataset,
                caption=captions[n] if captions else None,
                license="generated",
                rights_ref="fixture://access-control",
            ),
            "qa-acl-" + dataset,
            index.id,
        )
        images.append(UUID(body["image_id"]))
    await Worker(services, encoder, index.id).run(once=True)
    assert (await verify_index(services, index.id, mark_ready=True))["status"] == "pass"
    async with services.database.sessions() as session, session.begin():
        session.add(
            ActiveSearchIndex(
                corpus_key="default", index_id=index.id, generation=1, activated_at=now()
            )
        )
    runtime = SearchRuntime(services)
    runtime.encoder = encoder
    runtime.registry = SearchRegistry(services, encoder)
    await runtime.registry.load()
    runtime.available = True
    app.state.search_runtime = runtime
    app.state.settings.search_enabled = True
    return runtime, images


async def test_dataset_scope_search_media_rag_grants_hide_and_metadata(accounts, qa_resources):
    app, admin, user, _, uid = accounts
    runtime, ids = await seed_search(qa_resources, app)
    try:
        response = await admin.get("/api/v1/admin/datasets")
        assert response.status_code == 200, response.text
        datasets = response.json()["datasets"]
        dataset = next(d for d in datasets if d["key"] == "private_a")
        assert (await user.get(f"/api/v1/images/{ids[0]}")).status_code == 404
        empty = await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})
        assert empty.status_code == 200 and empty.json()["total_results"] == 0, empty.text
        assert (
            await admin.put(
                f"/api/v1/admin/users/{uid}/datasets", json={"dataset_ids": [dataset["id"]]}
            )
        ).status_code == 200
        response = await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})
        assert response.status_code == 200, response.text
        assert [r["image_id"] for r in response.json()["results"]] == [str(ids[0])]
        assert (await user.get(f"/api/v1/images/{ids[1]}/content")).status_code == 404
        assert (await user.get(f"/api/v1/images/{ids[0]}/content")).status_code == 200
        scope = current_principal.set(
            Principal(UUID(uid), "reader", "user", (UUID(dataset["id"]),), ("private_a",))
        )
        try:
            evidence, _, excluded = await EvidenceRetriever(runtime).retrieve(ids)
            assert [e.image_id for e in evidence] == [ids[0]] and str(ids[1]) in excluded
            candidates = await VectorRetriever(qa_resources.services, runtime.registry).search(
                np.ones(8), 10, Filters()
            )
            assert [c.image_id for c in candidates] == [ids[0]]
        finally:
            current_principal.reset(scope)
        # User requests are denied before parsing mutation bodies.
        for method, path in [
            ("POST", "/admin/images/upload"),
            ("PATCH", f"/admin/images/{ids[0]}"),
            ("DELETE", f"/admin/images/{ids[0]}"),
            ("PUT", f"/admin/users/{uid}/datasets"),
            ("POST", "/admin/knowledge"),
            ("POST", "/admin/indexes/activate"),
        ]:
            assert (await user.request(method, "/api/v1" + path, json={})).status_code == 403
        assert (await admin.delete(f"/api/v1/admin/images/{ids[0]}")).status_code == 200
        assert (await user.get(f"/api/v1/images/{ids[0]}/content")).status_code == 404
        assert (await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})).json()[
            "total_results"
        ] == 0
        assert (await admin.post(f"/api/v1/admin/images/{ids[0]}/restore")).status_code == 200
        edit = await admin.patch(
            f"/api/v1/admin/images/{ids[0]}",
            json={
                "title": "Updated title",
                "caption": "Updated caption",
                "dataset_id": dataset["id"],
                "tags": ["updated"],
            },
        )
        assert edit.status_code == 200, edit.text
        assert (await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})).json()[
            "total_results"
        ] == 0
        await Worker(qa_resources.services, runtime.encoder, runtime.registry.index.id).run(
            once=True
        )
        assert (await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})).json()[
            "total_results"
        ] == 1
        assert (await user.get("/api/v1/system/workspace")).json()["dataset"]["images"] == 1
        assert (
            await admin.put(f"/api/v1/admin/users/{uid}/datasets", json={"dataset_ids": []})
        ).status_code == 200
        assert (await user.get(f"/api/v1/images/{ids[0]}/content")).status_code == 404
        assert (await user.get("/api/v1/auth/me")).json()["user"]["datasets"] == []
        app.state.settings.user_search_per_minute = 1
        assert (
            await user.post("/api/v1/search", json={"mode": "text", "text": "a shape"})
        ).status_code == 429
        app.state.settings.user_agent_per_day = 0
        assert (
            await user.post("/api/v1/search/agent", json={"query": "a shape"})
        ).status_code == 429
        app.state.settings.user_rag_per_day = 0
        assert (
            await user.post(
                "/api/v1/rag/explain", json={"query": "a shape", "question": "What is shown?"}
            )
        ).status_code == 429
    finally:
        await runtime.close()


async def test_expiry_disabled_login_throttle_and_quota(accounts, qa_resources):
    app, admin, user, _, uid = accounts
    app.state.settings.auth_login_attempts_per_minute = 3
    for _ in range(3):
        response = await user.post(
            "/api/v1/auth/login", json={"username": "unknown", "password": "wrong"}
        )
        assert response.status_code == 401
    assert (
        await user.post("/api/v1/auth/login", json={"username": "unknown", "password": "wrong"})
    ).status_code == 429
    async with qa_resources.services.database.sessions() as session, session.begin():
        rows = (
            await session.scalars(select(AuthSession).where(AuthSession.user_id == UUID(uid)))
        ).all()
        for row in rows:
            row.expires_at = now() - timedelta(seconds=1)
    assert (await user.get("/api/v1/system/workspace")).status_code == 401
    assert (
        await admin.patch(f"/api/v1/admin/users/{uid}", json={"is_active": False})
    ).status_code == 200
    assert (
        await user.post("/api/v1/auth/login", json={"username": "reader", "password": PASSWORD})
    ).status_code == 401


async def test_admin_upload_index_activation_and_knowledge_scope(accounts, qa_resources):
    import json
    from uuid import uuid4

    from app.repositories.knowledge_repository import KnowledgeRepository

    app, admin, _, _, uid = accounts
    runtime, ids = await seed_search(qa_resources, app)
    try:
        datasets = (await admin.get("/api/v1/admin/datasets")).json()["datasets"]
        dataset = next(d for d in datasets if d["key"] == "private_a")
        for _ in range(2):
            uploaded = await admin.post(
                "/api/v1/admin/images/upload",
                files={"image": ("test.png", image_bytes(2), "image/png")},
                data={
                    "dataset_id": dataset["id"],
                    "metadata": json.dumps(
                        {
                            "title": "Uploaded test image",
                            "license": "generated",
                            "rights_ref": "fixture://access",
                        }
                    ),
                },
                headers={"Idempotency-Key": "qa-admin-upload"},
            )
            assert uploaded.status_code == 202, uploaded.text
        await Worker(qa_resources.services, runtime.encoder, runtime.registry.index.id).run(
            once=True
        )
        created = await admin.post(
            "/api/v1/admin/indexes",
            json={
                "model_id": str(runtime.registry.model.id),
                "version": "qa_access_" + uuid4().hex[:12],
            },
        )
        assert created.status_code == 201, created.text
        index_id = UUID(created.json()["id"])
        queued = await admin.post(
            "/api/v1/admin/indexes/reindex", json={"target_index_id": str(index_id)}
        )
        assert queued.status_code == 202, queued.text
        await Worker(qa_resources.services, runtime.encoder, index_id).run(once=True)
        verified = await admin.post(
            "/api/v1/admin/indexes/verify", json={"index_id": str(index_id)}
        )
        assert verified.status_code == 200 and verified.json()["status"] == "pass", verified.text
        activated = await admin.post(
            "/api/v1/admin/indexes/activate", json={"index_id": str(index_id)}
        )
        assert activated.status_code == 200 and activated.json()["generation"] == 2, activated.text
        assert str(app.state.search_runtime.registry.index.id) == str(index_id)
        city, landmark, relationship = uuid4(), uuid4(), uuid4()
        payload = {
            "fixture": True,
            "entities": [
                {
                    "id": str(city),
                    "canonical_name": "QA Secret City",
                    "entity_type": "city",
                    "provenance": {"source_ref": "fixture://access"},
                },
                {
                    "id": str(landmark),
                    "canonical_name": "QA Secret Place",
                    "entity_type": "landmark",
                    "provenance": {"source_ref": "fixture://access"},
                },
            ],
            "relationships": [
                {
                    "id": str(relationship),
                    "subject_id": str(landmark),
                    "predicate": "located_in",
                    "object_id": str(city),
                    "source_ref": "fixture://access",
                    "evidence": {"fixture": True},
                    "verified_at": now().isoformat(),
                }
            ],
            "image_entities": [
                {
                    "image_id": str(ids[0]),
                    "entity_id": str(landmark),
                    "source_ref": "fixture://access",
                    "verified": True,
                }
            ],
        }
        for apply in [False, True]:
            imported = await admin.post(
                "/api/v1/admin/knowledge",
                json={"dataset_id": dataset["id"], "knowledge": payload, "apply": apply},
            )
            assert imported.status_code == 200, imported.text
        repository = KnowledgeRepository(qa_resources.services)
        scope = current_principal.set(Principal(UUID(uid), "reader", "user"))
        try:
            assert not (await repository.lookup("QA Secret Place")).entities
            assert not (await repository.relationships([landmark], "located_in")).relations
            assert not await repository.associations([landmark])
            current_principal.set(
                Principal(UUID(uid), "reader", "user", (UUID(dataset["id"]),), (dataset["key"],))
            )
            assert (await repository.lookup("QA Secret Place")).entity_ids == [landmark]
            assert len((await repository.relationships([landmark], "located_in")).relations) == 1
            assert len(await repository.associations([landmark])) == 1
        finally:
            current_principal.reset(scope)
    finally:
        await runtime.close()


async def test_worker_scheduler_skips_incompatible_and_leased_work(qa_resources):
    from app.cli.worker import pending_index
    from app.db.models.indexing import JobItem
    from app.services.embeddings.clip_encoder import fingerprint
    from app.services.indexing.collection_manager import CollectionManager

    class OtherEncoder(SyntheticEncoder):
        manifest = {**SyntheticEncoder.manifest, "revision": "other-fixture"}
        manifest_sha256 = fingerprint(manifest)

    services = qa_resources.services
    wrong, _ = await qa_resources.index(OtherEncoder())
    _, wrong_item = await ingest(
        services,
        image_bytes(0),
        ImageMetadataInput(
            source_dataset="wrong_model", license="generated", rights_ref="fixture://scheduler"
        ),
        "qa-wrong-model",
        wrong.id,
    )
    right, _ = await CollectionManager(services).register(
        SyntheticEncoder(), "qa_scheduler_" + qa_resources.token[:12]
    )
    _, right_item = await ingest(
        services,
        image_bytes(1),
        ImageMetadataInput(
            source_dataset="right_model", license="generated", rights_ref="fixture://scheduler"
        ),
        "qa-right-model",
        right.id,
    )
    assert await pending_index(services, SyntheticEncoder.manifest_sha256) == right.id
    assert await pending_index(services, SyntheticEncoder.manifest_sha256, [right.id]) is None
    async with services.database.sessions() as session, session.begin():
        item = await session.scalar(
            select(JobItem).where(JobItem.job_id == UUID(right_item["job_id"]))
        )
        item.status = "retry_wait"
        item.next_attempt_at = now() + timedelta(minutes=5)
    assert await pending_index(services, SyntheticEncoder.manifest_sha256) is None
