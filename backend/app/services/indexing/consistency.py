import json
from time import perf_counter

import numpy as np
from sqlalchemy import select

from app.db.models import EmbeddingModel, Image, SearchIndex
from app.db.models.indexing import ImageEmbedding, ImageObject, JobItem
from app.services.embeddings.vector_utils import vector_hash
from app.services.indexing.collection_manager import CollectionManager
from app.services.indexing.jobs import lock, new_item, new_job, now
from app.services.ingestion.storage import get_original, object_key


async def verify_index(services, index_id, repair=False, mark_ready=False):
    start = perf_counter()
    async with services.database.sessions() as session:
        index = await session.get(SearchIndex, index_id)
        if index is None:
            raise ValueError("INDEX_NOT_FOUND")
        model = await session.get(EmbeddingModel, index.model_id)
        embeddings = list(
            (
                await session.scalars(
                    select(ImageEmbedding).where(
                        ImageEmbedding.index_id == index.id, ImageEmbedding.status == "ready"
                    )
                )
            ).all()
        )
        live = await session.scalar(
            select(JobItem.id)
            .where(
                JobItem.index_id == index.id,
                JobItem.status.in_(["awaiting_input", "queued", "processing", "retry_wait"]),
            )
            .limit(1)
        )
    async with services.database.sessions() as session:
        expected_image_ids = {
            str(value)
            for value in (
                await session.scalars(select(JobItem.image_id).where(JobItem.index_id == index.id))
            ).all()
            if value is not None
        }
    manager = CollectionManager(services)
    await manager.ensure(index, model)
    problems = []
    ids = []
    for embedding in embeddings:
        async with services.database.sessions() as session:
            image = await session.get(Image, embedding.image_id)
            receipt = await session.scalar(
                select(ImageObject).where(
                    ImageObject.image_id == image.id, ImageObject.role == "original"
                )
            )
        try:
            if (
                image.status != "available"
                or not receipt
                or embedding.source_sha256 != image.sha256
                or embedding.metadata_revision != image.metadata_revision
            ):
                raise ValueError("INVALID_PG_RECEIPT")
            await get_original(services, image)
            points = await services.qdrant.client.retrieve(
                index.collection_name, ids=[str(image.id)], with_payload=True, with_vectors=True
            )
            if len(points) != 1:
                raise ValueError("VECTOR_MISSING")
            point = points[0]
            vector = np.asarray(point.vector, dtype=np.float32)
            if (
                vector.shape != (model.dimension,)
                or not np.isfinite(vector).all()
                or not np.isclose(np.linalg.norm(vector), 1, atol=1e-5)
                or vector_hash(vector) != embedding.vector_sha256
            ):
                raise ValueError("VECTOR_CORRUPT")
            expected = {
                "image_id": str(image.id),
                "index_id": str(index.id),
                "manifest_sha256": model.manifest_sha256,
                "source_sha256": image.sha256,
                "metadata_revision": image.metadata_revision,
            }
            if any(point.payload.get(k) != v for k, v in expected.items()):
                raise ValueError("PAYLOAD_MISMATCH")
            ids.append(str(image.id))
        except Exception as exc:
            problems.append(
                {
                    "image_id": str(image.id),
                    "code": str(exc) if isinstance(exc, ValueError) else "STORAGE_UNAVAILABLE",
                }
            )
            if repair:
                async with services.database.sessions() as session, session.begin():
                    await lock(session, "task:" + str(image.id) + str(index.id))
                    current = await session.get(
                        ImageEmbedding, (image.id, index.id), with_for_update=True
                    )
                    current.status = "failed"
                    current.last_error_code = "RECONCILIATION_FAILED"
                    active = await session.scalar(
                        select(JobItem.id).where(
                            JobItem.image_id == image.id,
                            JobItem.index_id == index.id,
                            JobItem.status.in_(
                                ["awaiting_input", "queued", "processing", "retry_wait"]
                            ),
                        )
                    )
                    if not active and image.status == "available":
                        job = new_job(session, index.id, kind="reindex")
                        await session.flush()
                        new_item(session, job, image, index.id)
    count = (await services.qdrant.client.count(index.collection_name, exact=True)).count
    expected_ids = set(ids) | {p["image_id"] for p in problems}
    point_ids = set()
    offset = None
    while True:
        points, offset = await services.qdrant.client.scroll(
            index.collection_name, limit=100, offset=offset, with_payload=False, with_vectors=False
        )
        point_ids.update(str(p.id) for p in points)
        if offset is None:
            break
    orphans = sorted(point_ids - expected_ids)
    # Không xóa orphan tự động: có thể là vector từ external write trước PG commit.
    missing_embeddings = sorted(expected_image_ids - set(ids))
    status = (
        "pass"
        if not problems
        and not orphans
        and not live
        and not missing_embeddings
        and ids
        and count == len(ids)
        else "incomplete"
    )
    report = {
        "status": status,
        "index_id": str(index.id),
        "collection": index.collection_name,
        "manifest_sha256": model.manifest_sha256,
        "dimension": model.dimension,
        "verified_images": len(ids),
        "exact_vector_count": count,
        "image_ids": sorted(ids),
        "problems": problems,
        "orphan_point_ids": orphans,
        "live_items": bool(live),
        "missing_embedding_image_ids": missing_embeddings,
        "verification_ms": (perf_counter() - start) * 1000,
    }
    if mark_ready:
        if status != "pass":
            raise ValueError("INDEX_NOT_VALIDATED")
        async with services.database.sessions() as session, session.begin():
            await lock(session, "index:" + str(index.id))
            index = await session.get(SearchIndex, index.id, with_for_update=True)
            pending = await session.scalar(
                select(JobItem.id)
                .where(
                    JobItem.index_id == index.id,
                    JobItem.status.in_(["awaiting_input", "queued", "processing", "retry_wait"]),
                )
                .limit(1)
            )
            current_ids = set(
                (
                    await session.scalars(
                        select(ImageEmbedding.image_id).where(
                            ImageEmbedding.index_id == index.id, ImageEmbedding.status == "ready"
                        )
                    )
                ).all()
            )
            if pending or {str(value) for value in current_ids} != set(ids):
                raise ValueError("INDEX_CHANGED_DURING_VALIDATION")
            index.status = "ready"
            index.validated_at = now()
            index.corpus_snapshot_ref = (
                "sha256:"
                + __import__("hashlib").sha256(json.dumps(sorted(ids)).encode()).hexdigest()
            )
        report["index_status"] = "ready"
    return report


async def object_orphans(services):
    async with services.database.sessions() as session:
        images = (await session.scalars(select(Image).where(Image.sha256.is_not(None)))).all()
    expected = {object_key(image) for image in images}

    def scan():
        names = []
        for entry in services.minio.client.list_objects(
            services.minio.bucket, prefix="images/original/", recursive=True
        ):
            names.append(entry.object_name)
            if len(names) > 10000:
                break
        return names

    actual = await services.minio.run(scan)
    return {
        "orphan_object_keys": sorted(set(actual) - expected),
        "scan_truncated": len(actual) > 10000,
        "action": "report_only_no_deletion",
    }
