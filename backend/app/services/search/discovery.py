"""Fresh, permission-scoped gallery samples without embedding inference."""

import hashlib
from uuid import UUID, uuid4

from sqlalchemy import String, cast, func, select, tuple_

from app.core.access import source_clause, visible_image_clause
from app.db.models import Image, ImageMetadata
from app.schemas.search import SearchResult


def discovery_statement(limit, seed, cursor=None):
    order_key = func.md5(cast(Image.id, String) + str(seed))
    statement = (
        select(Image, ImageMetadata)
        .join(ImageMetadata, ImageMetadata.image_id == Image.id)
        .where(
            Image.status == "available",
            Image.deleted_at.is_(None),
            source_clause(),
            visible_image_clause(Image.id),
        )
        .order_by(order_key, Image.id)
        .limit(limit)
    )
    if cursor:
        key, image_id = cursor.split(":")
        statement = statement.where(tuple_(order_key, Image.id) > tuple_(key, UUID(image_id)))
    return statement


async def discover_images(services, limit, seed=None, cursor=None):
    seed = seed or uuid4()
    async with services.database.sessions() as session:
        rows = (await session.execute(discovery_statement(limit + 1, seed, cursor))).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    results = []
    for rank, (image, meta) in enumerate(rows, 1):
        url = f"/api/v1/images/{image.id}/content"
        results.append(SearchResult(
            image_id=image.id, rank=rank, score=0,
            image_url=url + "?variant=original",
            thumbnail_url=url + "?variant=thumbnail",
            metadata={
                "title": meta.title, "caption": meta.caption,
                "width": image.width, "height": image.height,
                "media_type": image.media_type, "tags": [],
                "source_dataset": meta.source_dataset,
                "city": meta.city, "license": meta.license,
            },
        ))
    next_cursor = None
    if has_more and rows:
        image_id = rows[-1][0].id
        key = hashlib.md5((str(image_id) + str(seed)).encode(), usedforsecurity=False).hexdigest()
        next_cursor = f"{key}:{image_id}"
    return {
        "results": results, "total_results": len(results),
        "seed": str(seed), "has_more": has_more, "next_cursor": next_cursor,
    }
