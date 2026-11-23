"""Read current authoritative evidence in batches; never trust client metadata."""

import re

from sqlalchemy import select

from app.db.models.indexing import ImageTag
from app.repositories.image_repository import ImageRepository
from app.schemas.rag import ImageEvidence, RagImage
from app.schemas.search import ResultMetadata
from app.services.search.search_service import SearchService

INSTRUCTIONS = re.compile(
    r"ignore.{0,30}(instruction|previous|system)|system\s*prompt|api[_ ]?key|"
    r"reveal.{0,25}(secret|token)|bỏ\s*qua.{0,25}(hướng dẫn|chỉ dẫn)|"
    r"tiết lộ.{0,25}(khóa|bí mật)",
    re.I,
)


def safe_value(value, limit=1200):
    if not isinstance(value, str) or not value.strip() or INSTRUCTIONS.search(value):
        return None
    # Omit whole fields instead of turning a truncated caption into a different claim.
    return value.strip() if len(value.encode()) <= limit else None


class EvidenceRetriever:
    def __init__(self, runtime):
        self.runtime = runtime
        self.services = runtime.services
        self.repository = ImageRepository(self.services)

    async def retrieve(self, ids, retrieved=None):
        await self.runtime.registry.check()
        index = self.runtime.registry.index
        model = self.runtime.registry.model
        unique = list(dict.fromkeys(ids))
        rows, tags = await self.repository.candidates(unique, index.id)
        points = (
            await self.services.qdrant.client.retrieve(
                index.collection_name,
                ids=[str(i) for i in rows],
                with_payload=True,
                with_vectors=False,
            )
            if rows
            else []
        )
        payloads = {str(p.id): p.payload or {} for p in points}
        async with self.services.database.sessions() as session:
            tag_rows = (
                (await session.execute(select(ImageTag).where(ImageTag.image_id.in_(unique))))
                .scalars()
                .all()
                if unique
                else []
            )
        tag_provenance = {}
        for tag in tag_rows:
            tag_provenance.setdefault(tag.image_id, {})[tag.tag] = {
                "source": tag.source,
                "verified": tag.verified,
            }
        evidence, results, excluded = [], [], []
        original = {r.image_id: r for r in retrieved or []}
        search = SearchService(self.runtime)
        for rank, identity in enumerate(unique, 1):
            row = rows.get(identity)
            if row is None:
                excluded.append(str(identity))
                continue
            image, metadata, embedding, receipt = row
            expected = {
                "image_id": str(image.id),
                "index_id": str(index.id),
                "manifest_sha256": model.manifest_sha256,
                "source_sha256": image.sha256,
                "metadata_revision": image.metadata_revision,
            }
            payload = payloads.get(str(identity), {})
            if any(
                payload.get(k) != v for k, v in expected.items()
            ) or not await search.object_available(image, receipt):
                excluded.append(str(identity))
                continue
            caption = safe_value(metadata.caption) if metadata else None
            selected_tags = [t for t in tags[identity] if safe_value(t, 192)][:20]
            fields = {"width": image.width, "height": image.height, "media_type": image.media_type}
            if metadata:
                for key in ["title", "description", "source_dataset", "city", "license"]:
                    value = safe_value(getattr(metadata, key))
                    if value:
                        fields[key] = value
            provenance = {
                "metadata_revision": image.metadata_revision,
                "source_sha256": image.sha256,
                "index_id": str(index.id),
                "manifest_sha256": model.manifest_sha256,
                "caption": {
                    "source": safe_value(metadata.caption_source, 160) if metadata else None,
                    "verified": False,
                    "policy": "stored attribution; not visual verification",
                },
                "tags": tag_provenance.get(identity, {}),
                "metadata": {"source": "stored_postgresql", "verified_visual_content": False},
            }
            prior = original.get(identity)
            score = prior.score if prior else None
            evidence.append(
                ImageEvidence(
                    image_id=identity,
                    retrieval_rank=prior.rank if prior else rank,
                    retrieval_score=score,
                    caption=caption,
                    tags=selected_tags,
                    metadata=fields,
                    provenance=provenance,
                    incomplete=not bool(caption or selected_tags or fields.get("description")),
                )
            )
            url = f"/api/v1/images/{identity}/content"
            results.append(
                RagImage(
                    image_id=identity,
                    rank=prior.rank if prior else rank,
                    score=score,
                    score_type=prior.score_type if prior else None,
                    image_url=url + "?variant=original",
                    thumbnail_url=url + "?variant=thumbnail",
                    metadata=ResultMetadata(
                        title=fields.get("title"),
                        caption=caption,
                        width=image.width,
                        height=image.height,
                        media_type=image.media_type,
                        tags=selected_tags,
                        source_dataset=fields.get("source_dataset"),
                        city=fields.get("city"),
                        license=fields.get("license"),
                    ),
                    constraint_assessments=prior.constraint_assessments if prior else [],
                )
            )
        return evidence, results, excluded
