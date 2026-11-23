import numpy as np
from qdrant_client import models as qm
from sqlalchemy import select

from app.db.models import EmbeddingModel, SearchIndex
from app.services.embeddings.clip_encoder import fingerprint


class CollectionManager:
    def __init__(self, services):
        self.services = services
        self.client = services.qdrant.client

    async def ensure(self, index, model):
        name = index.collection_name
        if not await self.client.collection_exists(name):
            await self.client.create_collection(
                name,
                vectors_config=qm.VectorParams(size=model.dimension, distance=qm.Distance.COSINE),
                metadata={
                    "manifest_sha256": model.manifest_sha256,
                    "index_id": str(index.id),
                    "config_sha256": index.config_sha256,
                },
            )
        info = await self.client.get_collection(name)
        vectors = info.config.params.vectors
        metadata = info.config.metadata or {}
        if (
            not isinstance(vectors, qm.VectorParams)
            or vectors.size != model.dimension
            or vectors.distance != qm.Distance.COSINE
            or metadata
            != {
                "manifest_sha256": model.manifest_sha256,
                "index_id": str(index.id),
                "config_sha256": index.config_sha256,
            }
        ):
            raise ValueError("MODEL_INDEX_MISMATCH")
        return info

    async def register(self, encoder, version):
        import re
        from uuid import uuid4

        if not re.fullmatch(r"[a-z0-9_]{1,40}", version):
            raise ValueError("INVALID_INDEX_VERSION")
        config = {
            "version": version,
            "manifest_sha256": encoder.manifest_sha256,
            "dimension": encoder.dimension,
            "distance": "cosine",
            "payload_version": 1,
        }
        name = "images_" + version + "_" + fingerprint(config)[:12]
        async with self.services.database.sessions() as session, session.begin():
            model = await session.scalar(
                select(EmbeddingModel).where(
                    EmbeddingModel.manifest_sha256 == encoder.manifest_sha256
                )
            )
            if model is None:
                model = EmbeddingModel(
                    id=uuid4(),
                    model_name=encoder.manifest["model_id"],
                    model_revision=encoder.manifest["revision"],
                    processor_revision=encoder.manifest["processor_revision"],
                    dimension=encoder.dimension,
                    precision="float32",
                    normalization="l2",
                    distance_metric="cosine",
                    manifest=encoder.manifest,
                    manifest_sha256=encoder.manifest_sha256,
                    license_ref=encoder.manifest.get(
                        "license_ref", "https://github.com/openai/CLIP/blob/main/LICENSE"
                    ),
                )
                session.add(model)
                await session.flush()
            index = await session.scalar(
                select(SearchIndex).where(SearchIndex.collection_name == name)
            )
            if index is None:
                index = SearchIndex(
                    id=uuid4(),
                    model_id=model.id,
                    collection_name=name,
                    status="building",
                    config=config,
                    config_sha256=fingerprint(config),
                    corpus_snapshot_ref="pending-validation",
                )
                session.add(index)
                await session.flush()
        await self.ensure(index, model)
        return index, model

    async def write(self, index, model, records, vectors):
        vectors = np.asarray(vectors, dtype=np.float32)
        if (
            not records
            or vectors.shape != (len(records), model.dimension)
            or not np.isfinite(vectors).all()
            or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5, rtol=0)
        ):
            raise ValueError("INVALID_EMBEDDING")
        await self.ensure(index, model)
        points = [
            qm.PointStruct(id=str(record["image_id"]), vector=vector.tolist(), payload=record)
            for record, vector in zip(records, vectors, strict=True)
        ]
        result = await self.client.upsert(index.collection_name, points=points, wait=True)
        if result.status != qm.UpdateStatus.COMPLETED:
            raise RuntimeError("UPSERT_NOT_APPLIED")
        stored = await self.client.retrieve(
            index.collection_name, ids=[p.id for p in points], with_payload=True, with_vectors=True
        )
        by_id = {str(p.id): p for p in stored}
        for point, vector in zip(points, vectors, strict=True):
            actual = by_id.get(str(point.id))
            if (
                actual is None
                or actual.payload != point.payload
                or not np.allclose(actual.vector, vector, atol=2e-6, rtol=1e-5)
            ):
                raise RuntimeError("VECTOR_VERIFY_FAILED")
        # Kiểm tra applied write, retrieval và exact query theo ID.
        for point in points:
            hit = await self.client.query_points(
                index.collection_name,
                query=point.vector,
                query_filter=qm.Filter(must=[qm.HasIdCondition(has_id=[point.id])]),
                limit=1,
                search_params=qm.SearchParams(exact=True),
            )
            if not hit.points or str(hit.points[0].id) != str(point.id):
                raise RuntimeError("VECTOR_NOT_QUERYABLE")
