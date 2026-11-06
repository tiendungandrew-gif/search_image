from dataclasses import dataclass
from uuid import UUID

import numpy as np
from qdrant_client import models as qm

from app.core.exceptions import AppError
from app.services.embeddings.clip_encoder import normalized_vectors


@dataclass
class Candidate:
    image_id: UUID
    score: float
    payload: dict


def payload_filter(filters, exclude_id=None):
    must = []
    for field in ["source_dataset", "city"]:
        if getattr(filters, field) is not None:
            must.append(
                qm.FieldCondition(key=field, match=qm.MatchValue(value=getattr(filters, field)))
            )
    if filters.media_types:
        must.append(qm.FieldCondition(key="media_type", match=qm.MatchAny(any=filters.media_types)))
    if filters.tags_any:
        must.append(qm.FieldCondition(key="tags", match=qm.MatchAny(any=filters.tags_any)))
    for tag in filters.tags_all:
        must.append(qm.FieldCondition(key="tags", match=qm.MatchValue(value=tag)))
    for field in ["width", "height"]:
        low, high = getattr(filters, "min_" + field), getattr(filters, "max_" + field)
        if low is not None or high is not None:
            must.append(qm.FieldCondition(key=field, range=qm.Range(gte=low, lte=high)))
    # captured_at chưa có payload projection ổn định: filter authoritative ở PostgreSQL.
    return qm.Filter(
        must=must, must_not=[qm.HasIdCondition(has_id=[str(exclude_id)])] if exclude_id else None
    )


class VectorRetriever:
    def __init__(self, services, registry):
        self.services = services
        self.registry = registry

    async def search(self, vector, candidate_count, filters, exclude_id=None):
        vector = normalized_vectors(
            np.asarray(vector).reshape(1, -1), self.registry.model.dimension
        )[0]
        try:
            response = await self.services.qdrant.client.query_points(
                self.registry.index.collection_name,
                query=vector.tolist(),
                limit=candidate_count,
                query_filter=payload_filter(filters, exclude_id),
                with_payload=True,
                with_vectors=False,
                timeout=self.services.settings.search_vector_timeout_seconds,
            )
        except TimeoutError:
            raise AppError(
                504, "VECTOR_TIMEOUT", "Vector retrieval hết thời gian", retryable=True
            ) from None
        except Exception:
            raise AppError(
                503, "DEPENDENCY_UNAVAILABLE", "Không truy vấn được vector service", retryable=True
            ) from None
        return [
            Candidate(UUID(str(point.id)), float(point.score), point.payload or {})
            for point in response.points
            if np.isfinite(point.score)
        ]
