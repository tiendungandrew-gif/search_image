"""Bounded catalog completions using the existing metadata GIN index and image ACLs."""

from sqlalchemy import func, literal_column, select

from app.core.access import source_clause, visible_image_clause
from app.db.models import Image, ImageMetadata
from app.services.search.text_matching import fold_text


def prefix_query(value):
    words = fold_text(value).split()
    if not words or len(fold_text(value)) < 2:
        return None
    # Only folded alphanumeric tokens enter tsquery syntax; the value is still bound.
    return " & ".join(words[:-1] + [words[-1] + ":*"])


def catalog_suggestions(rows, value, limit=5):
    query = fold_text(value)
    words = query.split()
    if not words:
        return []
    matches = {}
    for row in rows:
        extra = row.extra if isinstance(row.extra, dict) else {}
        aliases = extra.get("approved_csv_rows", [])
        names = [row.title]
        if isinstance(aliases, list):
            names += [item.get("entity_name") for item in aliases if isinstance(item, dict)]
        # Short captions also support datasets whose images have no catalog title.
        names += [row.caption]
        for name in names:
            if not isinstance(name, str):
                continue
            name = " ".join(name.split())
            if not 2 <= len(name) <= 256:
                continue
            folded = fold_text(name)
            tokens = folded.split()
            if not all(word in tokens for word in words[:-1]) or not any(
                token.startswith(words[-1]) for token in tokens
            ):
                continue
            score = 0 if folded == query else 1 if folded.startswith(query) else 2
            previous = matches.get(folded)
            candidate = (score, len(name), name)
            if previous is None or candidate < previous:
                matches[folded] = candidate
    return [
        {"text": name, "label": "Có trong thư viện của bạn"}
        for _, _, name in sorted(matches.values())[:limit]
    ]


async def search_suggestions(services, value, limit=5, source_dataset=None):
    expression = prefix_query(value)
    if expression is None:
        return []
    query = func.to_tsquery(literal_column("'simple'::regconfig"), expression)
    statement = (
        select(ImageMetadata.title, ImageMetadata.caption, ImageMetadata.extra)
        .join(Image, Image.id == ImageMetadata.image_id)
        .where(
            Image.status == "available",
            Image.deleted_at.is_(None),
            source_clause(),
            visible_image_clause(Image.id),
            ImageMetadata.search_document.op("@@")(query),
        )
        .order_by(func.ts_rank_cd(ImageMetadata.search_document, query).desc(), Image.id)
        .limit(100)
    )
    if source_dataset:
        statement = statement.where(ImageMetadata.source_dataset == source_dataset)
    async with services.database.sessions() as session:
        rows = (await session.execute(statement)).all()
    return catalog_suggestions(rows, value, limit)
