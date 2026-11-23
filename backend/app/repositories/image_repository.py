import re
from collections import defaultdict

from sqlalchemy import Text, exists, func, literal_column, select

from app.core.access import source_clause, visible_image_clause
from app.db.models import Image, ImageMetadata
from app.db.models.indexing import ImageEmbedding, ImageObject, ImageTag


class ImageRepository:
    def __init__(self, services):
        self.services = services

    @staticmethod
    def candidate_statement(ids, index_id):
        statement = (
            select(Image, ImageMetadata, ImageEmbedding, ImageObject)
            .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
            .join(ImageEmbedding, ImageEmbedding.image_id == Image.id)
            .join(ImageObject, ImageObject.image_id == Image.id)
            .where(
                Image.status == "available",
                ImageEmbedding.index_id == index_id,
                ImageEmbedding.status == "ready",
                ImageEmbedding.source_sha256 == Image.sha256,
                ImageEmbedding.metadata_revision == Image.metadata_revision,
                ImageObject.role == "original",
                ImageObject.deleted_at.is_(None),
                ImageObject.sha256 == Image.sha256,
                source_clause(),
                visible_image_clause(Image.id),
            )
        )
        return statement.where(Image.id.in_(ids)) if ids is not None else statement

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

    async def text_candidates(self, text, index_id, filters, limit=50):
        from app.services.search.text_matching import (
            TextHit,
            accented_words,
            fold_text,
            matches_name,
            matches_phrase,
            short_phrase,
        )

        folded = fold_text(text)
        if not folded:
            return []
        query = func.plainto_tsquery(literal_column("'simple'::regconfig"), folded)
        explicit_accents = accented_words(text)
        concept_match = None
        if len(folded.split()) <= 2:
            # Retrieve folded terms first, then preserve each explicitly accented word.
            document = func.ts_filter(
                ImageMetadata.search_document, literal_column("ARRAY['B']::\"char\"[]")
            )
            rank = func.ts_rank_cd(document, query, 34)
            concept_match = document.op("@@")(query)
        else:
            rank = func.ts_rank_cd(ImageMetadata.search_document, query, 32)
        # Every retrieval channel shares the authoritative eligibility predicates.
        statement = (
            self.candidate_statement(None, index_id)
            .with_only_columns(
                Image.id, ImageMetadata.title, ImageMetadata.extra, rank.label("text_rank"),
                ImageMetadata.caption, ImageMetadata.description,
                maintain_column_froms=True,
            )
            .where(ImageMetadata.search_document.op("@@")(query))
        )
        if concept_match is not None:
            statement = statement.where(concept_match)
        if explicit_accents and concept_match is not None:
            original = func.lower(func.normalize(func.concat_ws(
                " ", ImageMetadata.caption, ImageMetadata.description
            ), literal_column("NFC")))
            for word in explicit_accents:
                statement = statement.where(original.op("~")(r"\m" + re.escape(word) + r"\M"))
        if explicit_accents and concept_match is None:
            aliases = func.jsonb_path_query_array(
                ImageMetadata.extra,
                literal_column("'$.approved_csv_rows[*].entity_name'::jsonpath"),
            ).cast(Text)
            original = func.lower(func.normalize(func.concat_ws(
                " ", ImageMetadata.title, ImageMetadata.caption, ImageMetadata.description, aliases
            ), literal_column("NFC")))
            for word in explicit_accents:
                # Folded GIN retrieves candidates; exact Unicode words preserve the intended sense.
                statement = statement.where(original.op("~")(r"\m" + re.escape(word) + r"\M"))
        if filters.image_ids is not None:
            statement = statement.where(Image.id.in_(filters.image_ids))
        for field in ["source_dataset", "city"]:
            expected = getattr(filters, field)
            if expected is not None:
                column = getattr(ImageMetadata, field)
                statement = statement.where(
                    column.is_(None) if field == "source_dataset" and expected == "__unassigned__"
                    else column == expected
                )
        if filters.media_types:
            statement = statement.where(Image.media_type.in_(filters.media_types))
        for field in ["width", "height"]:
            if (low := getattr(filters, "min_" + field)) is not None:
                statement = statement.where(getattr(Image, field) >= low)
            if (high := getattr(filters, "max_" + field)) is not None:
                statement = statement.where(getattr(Image, field) <= high)
        if filters.captured_from:
            statement = statement.where(ImageMetadata.captured_at >= filters.captured_from)
        if filters.captured_to:
            statement = statement.where(ImageMetadata.captured_at <= filters.captured_to)
        if filters.tags_any:
            statement = statement.where(exists(select(ImageTag.image_id).where(
                ImageTag.image_id == Image.id, ImageTag.tag.in_(filters.tags_any)
            )))
        for tag in filters.tags_all:
            statement = statement.where(exists(select(ImageTag.image_id).where(
                ImageTag.image_id == Image.id, ImageTag.tag == tag
            )))
        if short_phrase(text):
            phrase_document = func.ts_filter(
                ImageMetadata.search_document, literal_column("ARRAY['B']::\"char\"[]")
            )
            phrase_query = func.phraseto_tsquery(literal_column("'simple'::regconfig"), folded)
            # Exact phrases enter the bounded candidate pool ahead of scattered tokens.
            statement = statement.order_by(phrase_document.op("@@")(phrase_query).desc())
        statement = statement.order_by(rank.desc(), Image.id).limit(min(1000, limit))
        async with self.services.database.sessions() as session:
            rows = (await session.execute(statement)).all()
        output = []
        for identity, title, extra, score, caption, description in rows:
            aliases = [
                r.get("entity_name", "")
                for r in (extra or {}).get("approved_csv_rows", []) if isinstance(r, dict)
            ]
            output.append(
                TextHit(identity, float(score), title, matches_name(text, [title, *aliases]),
                        matches_phrase(text, [caption, description]))
            )
        return sorted(
            output,
            key=lambda hit: (-hit.name_match, -hit.phrase_match, -hit.score, str(hit.image_id)),
        )
