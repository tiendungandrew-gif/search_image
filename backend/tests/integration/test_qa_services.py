"""Real disposable services with synthetic files/vectors, no AI accuracy claim."""

import asyncio
from uuid import UUID, uuid4

import httpx
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from qdrant_client import models as qm
from sqlalchemy import text

from app.main import create_app
from app.schemas.ingestion import ImageMetadataInput
from app.services.indexing.consistency import object_orphans, verify_index
from app.services.indexing.jobs import ingest, job_response, now
from app.services.indexing.worker import Worker
from tests.fixtures.synthetic import SyntheticEncoder, image_bytes

pytestmark = pytest.mark.integration


def metadata():
    return ImageMetadataInput(
        source_dataset="qa_synthetic_v1",
        title="Synthetic software fixture",
        license="generated-test-fixture",
        rights_ref="fixture://phase11/generated",
        tags=["qa", "synthetic"],
    )


async def test_empty_real_services_api_contract_and_private_access(qa_resources):
    cfg = qa_resources.settings
    assert await qa_resources.services.readiness() == {
        "postgresql": "healthy",
        "qdrant": "healthy",
        "minio": "healthy",
    }
    app = create_app(cfg)
    headers = {"Authorization": "Bearer " + cfg.api_token.get_secret_value()}
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app), base_url="http://qa") as client,
    ):
        assert (await client.get("/api/v1/health/live")).status_code == 200
        assert (await client.get("/api/v1/health/ready", headers=headers)).status_code == 200
        snapshot = await client.get("/api/v1/system/workspace", headers=headers)
        assert snapshot.json()["dataset"]["state"] == "empty_dataset"
        assert snapshot.json()["dataset"]["images"] == 0
        assert not any(snapshot.json()["capabilities"].values())
        for path in ["/api/v1/system/workspace", "/api/v1/system/evaluation"]:
            assert (await client.get(path)).status_code == 401
        disabled = await client.post("/api/v1/search", headers=headers, json={"text": "a shape"})
        assert (
            disabled.status_code == 409 and disabled.json()["error"]["code"] == "FEATURE_DISABLED"
        )


async def test_ingestion_three_formats_duplicates_and_real_vectors(qa_resources):
    services = qa_resources.services
    encoder = SyntheticEncoder()
    index, _ = await qa_resources.index(encoder)
    ids = []
    for number, media in enumerate(["JPEG", "PNG", "WEBP"]):
        raw = image_bytes(number, media)
        key = "qa-" + uuid4().hex
        first, second = await asyncio.gather(
            ingest(services, raw, metadata(), key, index.id),
            ingest(services, raw, metadata(), key, index.id),
            return_exceptions=True,
        )
        # A concurrent request may observe the documented in-progress conflict.
        accepted = next(row for row in [first, second] if isinstance(row, tuple))
        status, body = accepted
        assert status == 202
        assert await ingest(services, raw, metadata(), key, index.id) == accepted
        ids.append(body["image_id"])
    await Worker(services, encoder, index.id).run(once=True)
    report = await verify_index(services, index.id, mark_ready=True)
    assert report["status"] == "pass" and report["exact_vector_count"] == 3
    points = await services.qdrant.client.retrieve(
        index.collection_name, ids=ids, with_vectors=True
    )
    assert len(points) == 3 and all(np.isclose(np.linalg.norm(point.vector), 1) for point in points)
    filtered = await services.qdrant.client.query_points(
        index.collection_name,
        query=points[0].vector,
        query_filter=qm.Filter(
            must=[qm.FieldCondition(key="tags", match=qm.MatchValue(value="synthetic"))]
        ),
        limit=2,
    )
    assert len(filtered.points) == 2


async def test_zero_encoder_cannot_publish_a_successful_receipt(qa_resources):
    class ZeroEncoder(SyntheticEncoder):
        def encode_images(self, images):
            return np.zeros((len(images), self.dimension), dtype=np.float32)

    services = qa_resources.services
    encoder = ZeroEncoder()
    index, _ = await qa_resources.index(encoder)
    _, body = await ingest(services, image_bytes(), metadata(), "qa-zero-vector", index.id)
    await Worker(services, encoder, index.id).run(once=True)
    job = await job_response(services, UUID(body["job_id"]))
    assert job["status"] == "failed"
    assert job["items"][0]["last_error_code"] == "INVALID_EMBEDDING"
    assert (await services.qdrant.client.count(index.collection_name, exact=True)).count == 0


async def test_worker_lease_fencing_retry_and_consistency_repair(qa_resources, monkeypatch):
    from datetime import timedelta

    from app.db.models.indexing import JobItem

    services = qa_resources.services
    encoder = SyntheticEncoder()
    index, _ = await qa_resources.index(encoder)
    _, body = await ingest(services, image_bytes(), metadata(), "qa-worker-recovery", index.id)
    worker = Worker(services, encoder, index.id)
    await worker.configuration()
    abandoned = await worker.claim()
    async with services.database.sessions() as session, session.begin():
        item = await session.get(JobItem, abandoned[0].id)
        item.lease_expires_at = now() - timedelta(seconds=1)
    await worker.recover()
    assert not await worker.finish(abandoned[0], error="OLD_CLAIM")
    original = services.qdrant.client.upsert
    calls = 0

    async def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("synthetic RPC interruption")
        return await original(*args, **kwargs)

    monkeypatch.setattr(services.qdrant.client, "upsert", fail_once)
    await worker.process(await worker.claim())
    assert (await job_response(services, UUID(body["job_id"])))["counts"]["retry_wait"] == 1
    async with services.database.sessions() as session, session.begin():
        item = await session.get(JobItem, abandoned[0].id)
        item.next_attempt_at = now() - timedelta(seconds=1)
    await worker.process(await worker.claim())
    assert (await verify_index(services, index.id))["status"] == "pass"
    await services.qdrant.client.delete(index.collection_name, [body["image_id"]], wait=True)
    assert (await verify_index(services, index.id, repair=True))["problems"][0][
        "code"
    ] == "VECTOR_MISSING"
    await worker.run(once=True)
    assert (await verify_index(services, index.id))["status"] == "pass"


async def test_orphan_storage_detection_private_bucket_and_missing_object(qa_resources):
    import io

    services = qa_resources.services
    name = "images/original/qa-orphan.png"
    await services.minio.run(
        lambda: services.minio.client.put_object(
            services.minio.bucket, name, io.BytesIO(b"fixture"), 7, content_type="image/png"
        )
    )
    assert (await object_orphans(services))["orphan_object_keys"] == [name]
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://qa-minio:9000/{services.minio.bucket}/{name}")
    assert response.status_code == 403
    await services.minio.run(
        lambda: services.minio.client.remove_object(services.minio.bucket, name)
    )
    assert (await object_orphans(services))["orphan_object_keys"] == []


async def test_database_constraints_and_sql_injection_is_data(qa_resources):
    services = qa_resources.services
    async with services.database.sessions() as session:
        value = "Paris'); DROP TABLE images; --"
        assert await session.scalar(text("SELECT :city"), {"city": value}) == value
        assert await session.scalar(text("SELECT count(*) FROM images")) == 0
    index, _ = await qa_resources.index(SyntheticEncoder())
    _, body = await ingest(services, image_bytes(), metadata(), "qa-private-media", index.id)
    app = create_app(qa_resources.settings)
    app.state.services = services
    async with AsyncClient(transport=ASGITransport(app), base_url="http://qa") as client:
        path = f"/api/v1/images/{body['image_id']}/content?variant=original"
        # Guests may read public media; a private/non-published ID stays undiscoverable.
        assert (await client.get(path)).status_code == 404
        headers = {"Authorization": "Bearer " + qa_resources.settings.api_token.get_secret_value()}
        response = await client.get(path, headers=headers)
        assert response.status_code == 200 and response.content == image_bytes()
        assert response.headers["cache-control"] == "private, no-store"


async def test_worker_cancellation_keeps_images_alive_until_encoder_finishes(qa_resources):
    import threading

    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    failures = []

    class BlockingEncoder(SyntheticEncoder):
        def encode_images(self, images):
            entered.set()
            try:
                assert release.wait(3)
                return super().encode_images(images)
            except Exception as error:
                failures.append(type(error).__name__)
                raise
            finally:
                finished.set()

    services = qa_resources.services
    encoder = BlockingEncoder()
    index, _ = await qa_resources.index(encoder)
    await ingest(services, image_bytes(), metadata(), "qa-cancel-encoder", index.id)
    worker = Worker(services, encoder, index.id)
    await worker.configuration()
    process = asyncio.create_task(worker.process(await worker.claim()))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        process.cancel()
        with pytest.raises(asyncio.CancelledError):
            await process
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 2)
    assert not failures, "Cancellation closed PIL images while the real thread still used them"
    assert (await services.qdrant.client.count(index.collection_name, exact=True)).count == 0
