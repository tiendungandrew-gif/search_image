import os
import platform
import resource
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.container import Services
from app.db.models import ImageMetadata, SearchIndex
from app.db.models.indexing import ImageTag
from app.repositories.image_repository import ImageRepository


async def profile_services(snapshot):
    services = Services(Settings())
    try:
        ids = [UUID(row["image_id"]) for row in snapshot["images"]]
        statements = {
            "candidate_metadata": ImageRepository.candidate_statement(
                ids, UUID(snapshot["active"]["index_id"])
            ),
            "batch_tags": select(ImageTag.image_id, ImageTag.tag).where(ImageTag.image_id.in_(ids)),
        }
        plans = {}
        async with services.database.sessions() as session:
            index = await session.get(SearchIndex, UUID(snapshot["active"]["index_id"]))
            if index is None:
                raise ValueError("SNAPSHOT_INDEX_NOT_FOUND")
            collection_name = index.collection_name
            captions = await session.scalar(
                select(func.count())
                .select_from(ImageMetadata)
                .where(
                    ImageMetadata.image_id.in_(ids),
                    ImageMetadata.caption.is_not(None),
                    func.length(func.trim(ImageMetadata.caption)) > 0,
                )
            )
            tags = await session.scalar(
                select(func.count(func.distinct(ImageTag.image_id))).where(
                    ImageTag.image_id.in_(ids)
                )
            )
            for name, statement in statements.items():
                compiled = str(
                    statement.compile(
                        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                    )
                )
                plans[name] = (
                    await session.execute(
                        text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + compiled)
                    )
                ).scalar()
        collection = await services.qdrant.client.get_collection(collection_name)
        count = await services.qdrant.client.count(collection_name, exact=True)
        return {
            "status": "measured",
            "postgresql_plans": plans,
            "metadata_query_count": 2,
            "query_count_policy": "batch join and batch tags; independent of pool size",
            "corpus_metadata_coverage": {
                "images": len(ids),
                "images_with_nonempty_caption": captions,
                "images_with_tags": tags,
                "policy": "Presence only; not a claim of caption correctness or verified tags",
            },
            "connection_pool": services.database.engine.pool.status(),
            "qdrant": {
                "exact_points": count.count,
                "indexed_vectors_count": collection.indexed_vectors_count,
                "hnsw": collection.config.hnsw_config.model_dump(mode="json"),
                "optimizer": collection.config.optimizer_config.model_dump(mode="json"),
                "vectors": collection.config.params.vectors.model_dump(mode="json"),
                "payload_schema": {
                    key: value.model_dump(mode="json")
                    for key, value in collection.payload_schema.items()
                },
            },
            "worker_process": {
                "pid": os.getpid(),
                "platform": platform.platform(),
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            "gpu_measurements": None,
            "limitations": [
                "Small corpus may use sequential/plain scans; no artificial index forcing",
                "Pool status is a point-in-time observation, not a lifetime contention histogram",
            ],
        }
    finally:
        await services.close()
