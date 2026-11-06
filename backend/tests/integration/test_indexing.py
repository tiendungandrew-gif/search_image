"""Dùng infrastructure thật; fault injection chỉ ở đúng lời gọi upsert được nêu rõ."""

import asyncio
import hashlib
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import Settings
from app.db.models import Image, ImageMetadata, IndexingJob, SearchIndex
from app.db.models.indexing import (
    IdempotencyRecord,
    ImageEmbedding,
    ImageObject,
    ImageTag,
    JobAttempt,
    JobItem,
)
from app.main import create_app
from app.schemas.ingestion import ImageMetadataInput, JobInput
from app.services.embeddings.clip_encoder import ClipEncoder
from app.services.health import Services
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.consistency import verify_index
from app.services.indexing.jobs import ingest, job_response, now
from app.services.indexing.submission import submit_job
from app.services.indexing.worker import Worker
from app.services.ingestion.storage import object_key, put_original

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INDEXING_E2E") != "1",
        reason="Cần model cache/dataset thật và RUN_INDEXING_E2E=1",
    ),
]


async def test_real_model_batch_retry_recovery_idempotency_and_repair(monkeypatch):
    settings = Settings()
    services = Services(settings)
    encoder = await asyncio.to_thread(ClipEncoder, settings)
    index, _ = await CollectionManager(services).register(encoder, "test_" + uuid4().hex[:12])
    ids = []
    jobs = []
    keys = []
    image_owned = False
    owned_indexes = [index]
    bad_image = None
    try:
        data = await asyncio.to_thread(
            Path(settings.dataset_root, "sample", "coffee.png").read_bytes
        )
        metadata = ImageMetadataInput(
            source_dataset="scikit-image-v0.25.2",
            license="CC0-1.0",
            rights_ref="https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/data/_fetchers.py",
        )
        key = "test-" + uuid4().hex
        keys.append(key)
        settings.ingestion_index_id = str(index.id)
        app = create_app(settings)
        app.state.services = services
        # Fault injection ở PUT: bytes/job reservation phải resume cùng IDs.
        from app.services.indexing import jobs as jobs_module

        original_put = jobs_module.put_original
        writing = asyncio.Event()
        release_write = asyncio.Event()
        write_calls = 0

        async def interrupted_put(*args, **kwargs):
            nonlocal write_calls
            write_calls += 1
            if write_calls == 1:
                writing.set()
                await release_write.wait()
                raise TimeoutError("isolated injected storage interruption")
            return await original_put(*args, **kwargs)

        monkeypatch.setattr(jobs_module, "put_original", interrupted_put)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

            async def send_upload():
                return await client.post(
                    "/api/v1/images",
                    headers={
                        "Authorization": "Bearer " + settings.write_api_token.get_secret_value(),
                        "Idempotency-Key": key,
                    },
                    files={"image": ("untrusted-name.png", data, "image/png")},
                    data={"metadata": metadata.model_dump_json()},
                )

            uploading = asyncio.create_task(send_upload())
            await asyncio.wait_for(writing.wait(), timeout=10)
            try:
                inflight = await send_upload()
                assert inflight.status_code == 409 and inflight.headers["retry-after"] == "1"
            finally:
                release_write.set()
            interrupted = await uploading
            assert interrupted.status_code == 503
            async with services.database.sessions() as session:
                reservation = await session.get(IdempotencyRecord, ("operator", "/images", key))
                reserved = reservation.response_ref
            upload = await send_upload()
            assert upload.json() == reserved
            assert upload.status_code == 202, upload.json()
            status, response = upload.status_code, upload.json()
            body = await client.get(
                "/api/v1/images/" + response["image_id"] + "/content",
                headers={"Authorization": "Bearer " + settings.api_token.get_secret_value()},
            )
            assert body.content == data and body.headers["cache-control"] == "private, no-store"
        ids.append(response["image_id"])
        jobs.append(response["job_id"])
        image_owned = not response["duplicate"]
        assert status == 202
        assert await ingest(services, data, metadata, key, index.id) == (status, response)
        worker = Worker(services, encoder, index.id)
        await worker.configuration()
        claimed = await worker.claim()
        assert len(claimed) == 1
        # SKIP LOCKED/live status không cấp lại claim đang sống.
        assert await Worker(services, encoder, index.id).claim() == []
        async with services.database.sessions() as session, session.begin():
            item = await session.get(JobItem, claimed[0].id)
            item.lease_expires_at = now() - timedelta(seconds=1)
        await worker.recover()
        assert not await worker.finish(claimed[0], error="STALE_WRITER")
        original = services.qdrant.client.upsert
        calls = 0

        async def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TimeoutError("isolated injected transient Qdrant failure")
            return await original(*args, **kwargs)

        monkeypatch.setattr(services.qdrant.client, "upsert", fail_once)
        await worker.process(await worker.claim())
        first = await job_response(services, __import__("uuid").UUID(jobs[0]))
        assert first["counts"]["retry_wait"] == 1
        async with services.database.sessions() as session, session.begin():
            item = await session.get(JobItem, claimed[0].id)
            item.next_attempt_at = now() - timedelta(seconds=1)
        await worker.process(await worker.claim())
        report = await verify_index(services, index.id)
        assert report["status"] == "pass" and report["exact_vector_count"] == 1
        result = await job_response(services, __import__("uuid").UUID(jobs[0]))
        assert result["status"] == "succeeded" and result["items"][0]["attempt_count"] == 3
        key2 = "test-" + uuid4().hex
        keys.append(key2)
        duplicate = await ingest(services, data, metadata, key2, index.id)
        assert duplicate[0] == 200 and duplicate[1]["image_id"] == ids[0]
        # Missing vector thật -> reconcile, readiness của embedding bị hạ, durable repair task.
        await services.qdrant.client.delete(index.collection_name, [ids[0]], wait=True)
        report = await verify_index(services, index.id, repair=True)
        assert report["problems"][0]["code"] == "VECTOR_MISSING"
        await worker.run(once=True)
        assert (await verify_index(services, index.id))["status"] == "pass"
        # Reindex sang collection mới giữ collection/index cũ nguyên.
        index2, _ = await CollectionManager(services).register(encoder, "test_" + uuid4().hex[:12])
        owned_indexes.append(index2)
        key3 = "test-" + uuid4().hex
        keys.append(key3)
        new = await submit_job(
            services, JobInput(kind="reindex", target_index_id=index2.id, image_ids=ids), key3
        )
        jobs.append(new["job_id"])
        await Worker(services, encoder, index2.id).run(once=True)
        assert (await verify_index(services, index.id))["exact_vector_count"] == 1
        assert (await verify_index(services, index2.id))["exact_vector_count"] == 1
        # Fixture corrupt-storage cô lập: model vẫn thật, một ảnh lỗi không phá ảnh hợp lệ.
        bad_bytes = b"corrupt-fixture-" + uuid4().bytes
        bad_image = Image(
            id=uuid4(),
            sha256=hashlib.sha256(bad_bytes).hexdigest(),
            status="available",
            media_type="image/png",
            byte_size=len(bad_bytes),
            width=1,
            height=1,
            metadata_revision=1,
            created_by="integration-fixture",
        )
        async with services.database.sessions() as session, session.begin():
            session.add(bad_image)
            await session.flush()
            session.add(
                ImageMetadata(image_id=bad_image.id, source_dataset="isolated-corrupt-fixture")
            )
        await put_original(services, bad_image, bad_bytes)
        partial_key = "test-" + uuid4().hex
        keys.append(partial_key)
        partial = await submit_job(
            services,
            JobInput(
                kind="reindex",
                target_index_id=index2.id,
                image_ids=[__import__("uuid").UUID(ids[0]), bad_image.id],
            ),
            partial_key,
        )
        await Worker(services, encoder, index2.id).run(once=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": "Bearer " + settings.write_api_token.get_secret_value()}
            page = await client.get(
                "/api/v1/index/jobs/" + partial["job_id"] + "?limit=1", headers=headers
            )
            assert page.status_code == 200, page.json()
            value = page.json()
            assert value["status"] == "partial_failed"
            assert value["counts"]["succeeded"] == 1 and value["counts"]["failed"] == 1
            assert value["started_at"] and value["finished_at"] and value["next_cursor"]
            page2 = await client.get(
                "/api/v1/index/jobs/" + partial["job_id"],
                params={"limit": 1, "cursor": value["next_cursor"]},
                headers=headers,
            )
            assert page2.status_code == 200 and page2.json()["next_cursor"] is None
            assert page2.json()["items"][0]["item_id"] != value["items"][0]["item_id"]
    finally:
        # Cleanup đúng test UUID; giữ originals/metadata đã tồn tại trước test.
        # Chỉ các index UUID do chính test này tạo.
        for test_index in owned_indexes:
            await services.qdrant.client.delete_collection(test_index.collection_name)
            async with services.database.sessions() as session, session.begin():
                items = list(
                    (
                        await session.scalars(
                            select(JobItem).where(JobItem.index_id == test_index.id)
                        )
                    ).all()
                )
                job_ids = {x.job_id for x in items}
                item_ids = [x.id for x in items]
                await session.execute(delete(JobAttempt).where(JobAttempt.item_id.in_(item_ids)))
                await session.execute(delete(JobItem).where(JobItem.id.in_(item_ids)))
                await session.execute(delete(IndexingJob).where(IndexingJob.id.in_(job_ids)))
                await session.execute(
                    delete(ImageEmbedding).where(ImageEmbedding.index_id == test_index.id)
                )
                await session.delete(await session.get(SearchIndex, test_index.id))
        async with services.database.sessions() as session, session.begin():
            await session.execute(delete(IdempotencyRecord).where(IdempotencyRecord.key.in_(keys)))
            if bad_image is not None:
                await services.minio.run(
                    lambda: services.minio.client.remove_object(
                        services.minio.bucket, object_key(bad_image)
                    )
                )
                await session.execute(
                    delete(ImageMetadata).where(ImageMetadata.image_id == bad_image.id)
                )
                await session.delete(await session.get(Image, bad_image.id))
            if image_owned:
                image = await session.get(Image, __import__("uuid").UUID(ids[0]))
                await services.minio.run(
                    lambda: services.minio.client.remove_object(
                        services.minio.bucket, object_key(image)
                    )
                )
                for model in [ImageTag, ImageObject, ImageMetadata]:
                    await session.execute(delete(model).where(model.image_id == image.id))
                await session.delete(image)
        await services.close()
