import asyncio
import contextlib
import hashlib
import logging
import random
from datetime import timedelta
from time import perf_counter
from uuid import uuid4

import numpy as np
from sqlalchemy import or_, select, update

from app.core.exceptions import AppError
from app.db.models import EmbeddingModel, Image, ImageMetadata, SearchIndex
from app.db.models.indexing import ImageEmbedding, ImageTag, JobAttempt, JobItem
from app.services.embeddings.base import ImageEncoder
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.jobs import accept_original, now, summarize
from app.services.ingestion.storage import get_original
from app.services.ingestion.validator import prepared_image

logger = logging.getLogger("app.indexing")


def retry_delay(attempt):
    return min(60, 2**attempt) + random.uniform(0, 1)


def vector_hash(value):
    return hashlib.sha256(np.asarray(value, dtype="<f4").tobytes()).hexdigest()


class Worker:
    def __init__(self, services, encoder: ImageEncoder, index_id):
        self.services = services
        self.encoder = encoder
        self.index_id = index_id
        self.owner = str(uuid4())
        self.settings = services.settings
        self.manager = CollectionManager(services)
        self.batch_metrics = []

    async def configuration(self):
        async with self.services.database.sessions() as session:
            self.index = await session.get(SearchIndex, self.index_id)
            if not self.index or self.index.status not in {"building", "ready"}:
                raise ValueError("INVALID_INDEX")
            self.model = await session.get(EmbeddingModel, self.index.model_id)
            if self.model.manifest_sha256 != self.encoder.manifest_sha256:
                raise ValueError("MODEL_INDEX_MISMATCH")
        await self.manager.ensure(self.index, self.model)

    async def recover(self):
        # Revoke expired token trong transaction trước khi cấp claim mới.
        async with self.services.database.sessions() as session, session.begin():
            items = (
                await session.scalars(
                    select(JobItem)
                    .where(
                        JobItem.index_id == self.index_id,
                        JobItem.status == "processing",
                        JobItem.lease_expires_at < now(),
                    )
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for item in items:
                attempt = await session.get(JobAttempt, (item.id, item.attempt_count))
                attempt.finished_at = now()
                attempt.outcome = "lease_lost"
                attempt.error_code = "LEASE_EXPIRED"
                item.status = (
                    "retry_wait"
                    if item.attempt_count < self.settings.indexing_max_retries
                    else "failed"
                )
                item.claim_token = None
                item.lease_owner = None
                item.lease_expires_at = None
                item.next_attempt_at = now()
                item.last_error_code = "LEASE_EXPIRED"
                await session.flush()
                await summarize(session, item.job_id)
        async with self.services.database.sessions() as session:
            waiting = (
                await session.scalars(
                    select(JobItem)
                    .where(JobItem.index_id == self.index_id, JobItem.status == "awaiting_input")
                    .limit(100)
                )
            ).all()
        for item in waiting:
            try:
                await accept_original(self.services, item.image_id)
            except Exception:
                if (
                    now() - item.created_at
                ).total_seconds() > self.settings.indexing_job_timeout_seconds:
                    async with self.services.database.sessions() as session, session.begin():
                        current = await session.get(JobItem, item.id, with_for_update=True)
                        if current.status == "awaiting_input":
                            current.status = "failed"
                            current.last_error_code = "INPUT_NOT_DURABLE"
                            await session.flush()
                            await summarize(session, current.job_id)

    async def claim(self):
        async with self.services.database.sessions() as session, session.begin():
            rows = (
                await session.scalars(
                    select(JobItem)
                    .where(
                        JobItem.index_id == self.index_id,
                        JobItem.status.in_(["queued", "retry_wait"]),
                        or_(JobItem.next_attempt_at.is_(None), JobItem.next_attempt_at <= now()),
                    )
                    .order_by(JobItem.created_at, JobItem.id)
                    .with_for_update(skip_locked=True)
                    .limit(self.settings.embedding_batch_size)
                )
            ).all()
            for item in rows:
                image = await session.get(Image, item.image_id)
                embedding = await session.get(ImageEmbedding, (item.image_id, self.index_id))
                if embedding is None:
                    session.add(
                        ImageEmbedding(
                            image_id=image.id,
                            index_id=self.index_id,
                            status="processing",
                            source_sha256=image.sha256,
                            metadata_revision=image.metadata_revision,
                        )
                    )
                elif embedding.status != "ready":
                    embedding.status = "processing"
                item.status = "processing"
                item.attempt_count += 1
                item.claim_token = uuid4()
                item.lease_owner = self.owner
                item.lease_expires_at = now() + timedelta(
                    seconds=self.settings.indexing_lease_seconds
                )
                session.add(
                    JobAttempt(
                        item_id=item.id,
                        attempt_no=item.attempt_count,
                        claim_token=item.claim_token,
                        stage="object",
                    )
                )
                await session.flush()
                await summarize(session, item.job_id)
            return rows

    async def heartbeat(self, items):
        while True:
            await asyncio.sleep(self.settings.indexing_lease_seconds / 3)
            async with self.services.database.sessions() as session, session.begin():
                for item in items:
                    await session.execute(
                        update(JobItem)
                        .where(
                            JobItem.id == item.id,
                            JobItem.claim_token == item.claim_token,
                            JobItem.status == "processing",
                            JobItem.lease_expires_at > now(),
                        )
                        .values(
                            lease_expires_at=now()
                            + timedelta(seconds=self.settings.indexing_lease_seconds)
                        )
                    )

    async def finish(self, item, *, error=None, permanent=False, receipt=None, metrics=None):
        async with self.services.database.sessions() as session, session.begin():
            image = await session.get(Image, item.image_id, with_for_update=True)
            current = await session.get(JobItem, item.id, with_for_update=True)
            if (
                current.claim_token != item.claim_token
                or current.status != "processing"
                or current.lease_expires_at <= now()
            ):
                return False
            if image.status in {"deleting", "deleted"}:
                error = "IMAGE_DELETED"
                permanent = True
            attempt = await session.get(JobAttempt, (item.id, item.attempt_count))
            attempt.finished_at = now()
            attempt.stage = current.stage
            if error:
                retry = not permanent and item.attempt_count < self.settings.indexing_max_retries
                current.status = "retry_wait" if retry else "failed"
                current.next_attempt_at = (
                    now() + timedelta(seconds=retry_delay(item.attempt_count)) if retry else None
                )
                current.last_error_code = error
                attempt.outcome = "transient_failure" if retry else "permanent_failure"
                attempt.error_code = error
                embedding = await session.get(ImageEmbedding, (image.id, self.index_id))
                if embedding and embedding.status != "ready":
                    embedding.status = "failed"
                    embedding.last_error_code = error
            else:
                if (
                    receipt["source_sha256"] != image.sha256
                    or receipt["metadata_revision"] != image.metadata_revision
                ):
                    raise ValueError("STALE_SOURCE")
                embedding = await session.get(ImageEmbedding, (image.id, self.index_id))
                if embedding is None:
                    embedding = ImageEmbedding(
                        image_id=image.id,
                        index_id=self.index_id,
                        source_sha256=image.sha256,
                        metadata_revision=image.metadata_revision,
                    )
                    session.add(embedding)
                embedding.status = "ready"
                embedding.vector_sha256 = receipt["vector_sha256"]
                embedding.verified_at = now()
                embedding.last_error_code = None
                current.status = "succeeded"
                current.stage = "verify"
                current.last_error_code = None
                current.source_ref = {**current.source_ref, "metrics": metrics or {}}
                attempt.outcome = "succeeded"
            current.claim_token = None
            current.lease_owner = None
            current.lease_expires_at = None
            await session.flush()
            await summarize(session, current.job_id)
            logger.info(
                "index_item_finished",
                extra={
                    "job_id": str(current.job_id),
                    "item_id": str(current.id),
                    "image_id": str(image.id),
                    "index_id": str(self.index_id),
                    "stage": current.stage,
                    "attempt_no": item.attempt_count,
                    "error_category": current.last_error_code,
                },
            )
            return True

    async def stage(self, item, stage):
        async with self.services.database.sessions() as session, session.begin():
            result = await session.execute(
                update(JobItem)
                .where(
                    JobItem.id == item.id,
                    JobItem.claim_token == item.claim_token,
                    JobItem.status == "processing",
                    JobItem.lease_expires_at > now(),
                )
                .values(stage=stage)
            )
            if result.rowcount != 1:
                raise ValueError("LEASE_LOST")

    async def process(self, items):
        started = perf_counter()
        valid = []
        images = []
        payloads = []
        prep_ms = 0
        task = asyncio.create_task(self.heartbeat(items))
        try:
            for item in items:
                try:
                    await self.stage(item, "preprocess")
                    async with self.services.database.sessions() as session:
                        image = await session.get(Image, item.image_id)
                        if image.status != "available":
                            raise ValueError("IMAGE_NOT_AVAILABLE")
                        metadata = await session.get(ImageMetadata, image.id)
                        tags = list(
                            (
                                await session.scalars(
                                    select(ImageTag.tag).where(ImageTag.image_id == image.id)
                                )
                            ).all()
                        )
                    data = await get_original(self.services, image)
                    mark = perf_counter()
                    prepared = await asyncio.to_thread(prepared_image, data, self.settings)
                    prep_ms += (perf_counter() - mark) * 1000
                    payload = {
                        "image_id": str(image.id),
                        "index_id": str(self.index_id),
                        "manifest_sha256": self.model.manifest_sha256,
                        "source_sha256": image.sha256,
                        "metadata_revision": image.metadata_revision,
                        "image_status": "available",
                        "width": image.width,
                        "height": image.height,
                        "media_type": image.media_type,
                        "tags": tags,
                    }
                    for key in ["source_dataset", "city"]:
                        if getattr(metadata, key):
                            payload[key] = getattr(metadata, key)
                    images.append(prepared)
                    payloads.append(payload)
                    valid.append(item)
                except Exception as exc:
                    permanent = isinstance(exc, (AppError, ValueError))
                    await self.finish(
                        item,
                        error=exc.code
                        if isinstance(exc, AppError)
                        else ("INVALID_SOURCE" if permanent else "STORAGE_UNAVAILABLE"),
                        permanent=permanent,
                    )
            if not valid:
                return
            for item in valid:
                await self.stage(item, "embed")
            mark = perf_counter()
            vectors = await asyncio.to_thread(self.encoder.encode_images, images)
            embed_ms = (perf_counter() - mark) * 1000
            for item in valid:
                await self.stage(item, "vector")
            mark = perf_counter()
            await self.manager.write(self.index, self.model, payloads, vectors)
            stored = await self.services.qdrant.client.retrieve(
                self.index.collection_name, ids=[p["image_id"] for p in payloads], with_vectors=True
            )
            by_id = {str(p.id): p for p in stored}
            upsert_ms = (perf_counter() - mark) * 1000
            metrics = {
                **self.encoder.last_metrics,
                "batch_size": len(valid),
                "preprocess_ms": prep_ms,
                "embedding_ms": embed_ms,
                "upsert_verify_ms": upsert_ms,
                "batch_ms": (perf_counter() - started) * 1000,
            }
            for item, payload in zip(valid, payloads, strict=True):
                await self.stage(item, "verify")
                receipt = {
                    "source_sha256": payload["source_sha256"],
                    "metadata_revision": payload["metadata_revision"],
                    "vector_sha256": vector_hash(by_id[payload["image_id"]].vector),
                }
                await self.finish(item, receipt=receipt, metrics=metrics)
            self.batch_metrics.append(metrics)
            logger.info(
                "index_batch_complete",
                extra={
                    "duration_ms": metrics["batch_ms"],
                    "index_id": str(self.index_id),
                    "batch_size": len(valid),
                },
            )
        except Exception as exc:
            permanent = isinstance(exc, ValueError)
            for item in valid:
                await self.finish(
                    item,
                    error="INVALID_EMBEDDING" if permanent else "INDEXING_TRANSIENT_FAILURE",
                    permanent=permanent,
                )
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            for image in images:
                image.close()

    async def run(self, once=False):
        await self.configuration()
        while True:
            await self.recover()
            items = await self.claim()
            if items:
                async with asyncio.timeout(self.settings.indexing_job_timeout_seconds):
                    await self.process(items)
            elif once:
                return
            else:
                await asyncio.sleep(1)
