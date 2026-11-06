from collections import defaultdict

from sqlalchemy import select

from app.db.models import Image, ImageMetadata
from app.db.models.indexing import ImageEmbedding, ImageObject, ImageTag


class ImageRepository:
    def __init__(self, services):
        self.services = services

    @staticmethod
    def candidate_statement(ids, index_id):
        return (
            select(Image, ImageMetadata, ImageEmbedding, ImageObject)
            .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
            .join(ImageEmbedding, ImageEmbedding.image_id == Image.id)
            .join(ImageObject, ImageObject.image_id == Image.id)
            .where(
                Image.id.in_(ids),
                Image.status == "available",
                ImageEmbedding.index_id == index_id,
                ImageEmbedding.status == "ready",
                ImageEmbedding.source_sha256 == Image.sha256,
                ImageEmbedding.metadata_revision == Image.metadata_revision,
                ImageObject.role == "original",
                ImageObject.deleted_at.is_(None),
                ImageObject.sha256 == Image.sha256,
            )
        )

    async def candidates(self, ids, index_id):
        if not ids:
            return {}, {}
        async with self.services.database.sessions() as session:
            rows = (await session.execute(self.candidate_statement(ids, index_id))).all()
            tag_rows = (
                await session.execute(
                    select(ImageTag.image_id, ImageTag.tag).where(ImageTag.image_id.in_(ids))
                )
            ).all()
        tags = defaultdict(list)
        for image_id, tag in tag_rows:
            tags[image_id].append(tag)
        return {row[0].id: row for row in rows}, tags
