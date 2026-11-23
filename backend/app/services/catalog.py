"""Dataset catalog keyed by the existing authoritative source_dataset metadata."""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.access import UNASSIGNED
from app.db.models import Image, ImageMetadata
from app.db.models.access import AccessDataset


async def ensure_dataset(session, key):
    key = key if key is not None else UNASSIGNED
    query = insert(AccessDataset).values(
        id=uuid4(), key=key, name=key if key != UNASSIGNED else "Chưa phân loại"
    )
    await session.execute(query.on_conflict_do_nothing(index_elements=[AccessDataset.key]))


async def sync_catalog(session):
    keys = list(
        (
            await session.scalars(
                select(func.coalesce(ImageMetadata.source_dataset, UNASSIGNED))
                .select_from(Image)
                .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                .distinct()
            )
        ).all()
    )
    for key in keys:
        await ensure_dataset(session, key)
