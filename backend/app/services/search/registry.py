from uuid import UUID

from qdrant_client import models as qm
from qdrant_client.http.exceptions import UnexpectedResponse
from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.models import EmbeddingModel, SearchIndex
from app.db.models.indexing import ActiveSearchIndex
from app.services.embeddings.clip_encoder import fingerprint


class SearchRegistry:
    def __init__(self, services, encoder):
        self.services = services
        self.encoder = encoder

    async def load(self, index_id=None):
        async with self.services.database.sessions() as session:
            pointer = await session.get(ActiveSearchIndex, "default")
            selected = UUID(str(index_id)) if index_id else (pointer.index_id if pointer else None)
            if selected is None:
                raise AppError(503, "NOT_READY", "Chưa activate search index")
            index = await session.get(SearchIndex, selected)
            if not index or index.status != "ready" or index.validated_at is None:
                raise AppError(503, "NOT_READY", "Index chưa được kiểm chứng ready")
            model = await session.get(EmbeddingModel, index.model_id)
            if (
                model.manifest_sha256 != self.encoder.manifest_sha256
                or model.dimension != self.encoder.dimension
                or fingerprint(model.manifest) != model.manifest_sha256
                or fingerprint(index.config) != index.config_sha256
            ):
                raise AppError(
                    409, "MODEL_INDEX_MISMATCH", "Model/index manifest không tương thích"
                )
            self.index = index
            self.model = model
            self.generation = (
                pointer.generation if pointer and pointer.index_id == index.id else None
            )
        await self.collection()

    async def collection(self):
        try:
            info = await self.services.qdrant.client.get_collection(self.index.collection_name)
        except UnexpectedResponse as exc:
            if exc.status_code == 404:
                raise AppError(
                    503, "COLLECTION_UNAVAILABLE", "Collection không tồn tại", retryable=True
                ) from None
            raise AppError(
                503, "DEPENDENCY_UNAVAILABLE", "Vector service không khả dụng", retryable=True
            ) from None
        params = info.config.params.vectors
        expected = {
            "manifest_sha256": self.model.manifest_sha256,
            "index_id": str(self.index.id),
            "config_sha256": self.index.config_sha256,
        }
        if (
            not isinstance(params, qm.VectorParams)
            or params.size != self.model.dimension
            or params.distance != qm.Distance.COSINE
            or info.config.metadata != expected
        ):
            raise AppError(409, "MODEL_INDEX_MISMATCH", "Collection config không khớp registry")
        return info

    async def check(self):
        async with self.services.database.sessions() as session:
            row = (
                await session.execute(
                    select(ActiveSearchIndex, SearchIndex)
                    .join(SearchIndex, ActiveSearchIndex.index_id == SearchIndex.id)
                    .where(ActiveSearchIndex.corpus_key == "default")
                )
            ).first()
            if (
                not row
                or row[0].index_id != self.index.id
                or row[0].generation != self.generation
                or row[1].status != "ready"
                or row[1].model_id != self.model.id
            ):
                raise AppError(
                    503,
                    "INDEX_SWITCHING",
                    "Active index thay đổi; cần reload matching runtime",
                    retryable=True,
                )
        await self.collection()
