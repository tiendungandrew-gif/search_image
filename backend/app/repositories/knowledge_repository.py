"""Parameterized, bounded lookups. Fixtures are excluded from normal operation."""

import unicodedata

from sqlalchemy import exists, or_, select

from app.core.access import entity_clause, relation_clause, source_clause, visible_image_clause
from app.db.models import Image, ImageMetadata
from app.db.models.indexing import ImageEmbedding, ImageTag
from app.db.models.knowledge import Entity, EntityRelationship, ImageEntity
from app.schemas.agent import EntityRecord, ImageAssociation, KnowledgeEvidence, ToolOutput


def name_key(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


class KnowledgeRepository:
    def __init__(self, services):
        self.services = services
        self.allow_fixtures = services.settings.agent_allow_fixture_knowledge

    def entity_filter(self):
        return [entity_clause(Entity.id)] + (
            []
            if self.allow_fixtures
            else [
                Entity.provenance["fixture"].as_boolean().is_not(True),
                Entity.provenance["source_ref"].as_string().not_like("fixture:%"),
            ]
        )

    @staticmethod
    def record(entity):
        return EntityRecord(
            entity_id=entity.id,
            canonical_name=entity.canonical_name,
            entity_type=entity.entity_type,
            source_ref=entity.provenance.get("source_ref", ""),
            provenance=entity.provenance,
            fixture=bool(entity.provenance.get("fixture")),
        )

    async def lookup(self, name, entity_type=None):
        key = name_key(name)
        statement = select(Entity).where(
            or_(Entity.name_key == key, Entity.aliases.contains([key])), *self.entity_filter()
        )
        if entity_type:
            statement = statement.where(Entity.entity_type == entity_type)
        async with self.services.database.sessions() as session:
            rows = list((await session.scalars(statement.order_by(Entity.id).limit(6))).all())
        records = [self.record(row) for row in rows if row.provenance.get("source_ref")]
        return ToolOutput(
            entity_ids=[r.entity_id for r in records],
            entities=records,
            insufficient=len(records) != 1,
            warnings=["AMBIGUOUS_ENTITY"] if len(records) > 1 else [],
        )

    async def relationships(
        self, entity_ids, predicate, direction="out", entity_type=None, limit=50
    ):
        start = (
            EntityRelationship.subject_id if direction == "out" else EntityRelationship.object_id
        )
        target = (
            EntityRelationship.object_id if direction == "out" else EntityRelationship.subject_id
        )
        statement = (
            select(EntityRelationship, Entity)
            .join(Entity, Entity.id == target)
            .where(
                start.in_(entity_ids),
                EntityRelationship.predicate == predicate,
                EntityRelationship.verified_at.is_not(None),
                EntityRelationship.source_ref != "",
                *self.entity_filter(),
                relation_clause(EntityRelationship.id),
            )
        )
        if not self.allow_fixtures:
            statement = statement.where(
                EntityRelationship.evidence["fixture"].as_boolean().is_not(True),
                EntityRelationship.source_ref.not_like("fixture:%"),
            )
        if entity_type:
            statement = statement.where(Entity.entity_type == entity_type)
        async with self.services.database.sessions() as session:
            rows = (
                await session.execute(statement.order_by(EntityRelationship.id).limit(limit))
            ).all()
        entities = {e.id: self.record(e) for _, e in rows}
        relations = [
            KnowledgeEvidence(
                evidence_id=r.id,
                subject_id=r.subject_id,
                predicate=r.predicate,
                object_id=r.object_id,
                source_ref=r.source_ref,
                verified=True,
                provenance={**r.evidence, "verified_at": r.verified_at.isoformat()},
            )
            for r, _ in rows
        ]
        conflict = predicate == "located_in" and direction == "out" and len(entities) > 1
        return ToolOutput(
            entity_ids=sorted(entities, key=str),
            entities=list(entities.values()),
            relations=relations,
            insufficient=not entities or conflict,
            warnings=["CONFLICTING_RELATIONSHIPS"] if conflict else [],
        )

    async def associations(self, entity_ids):
        statement = (
            select(ImageEntity)
            .join(Entity, Entity.id == ImageEntity.entity_id)
            .join(Image, Image.id == ImageEntity.image_id)
            .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
            .where(
                ImageEntity.entity_id.in_(entity_ids),
                ImageEntity.verified.is_(True),
                ImageEntity.source_ref != "",
                *self.entity_filter(),
                source_clause(),
                visible_image_clause(Image.id),
                Image.status == "available",
            )
        )
        if not self.allow_fixtures:
            statement = statement.where(~ImageEntity.source_ref.startswith("fixture:"))
        async with self.services.database.sessions() as session:
            rows = (
                await session.scalars(statement.order_by(ImageEntity.image_id).limit(1000))
            ).all()
        return [
            ImageAssociation(
                image_id=r.image_id,
                entity_id=r.entity_id,
                relation=r.relation,
                source_ref=r.source_ref,
                verified=True,
            )
            for r in rows
        ]

    async def dataset_status(self, runtime):
        async with self.services.database.sessions() as session:
            any_image = await session.scalar(
                select(Image.id)
                .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                .where(Image.status == "available", source_clause(), visible_image_clause(Image.id))
                .limit(1)
            )
            if any_image is None:
                return "empty_dataset"
            if not runtime or not runtime.available:
                return "search_unavailable"
            ready = await session.scalar(
                select(ImageEmbedding.image_id)
                .join(Image, Image.id == ImageEmbedding.image_id)
                .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                .where(
                    ImageEmbedding.index_id == runtime.registry.index.id,
                    ImageEmbedding.status == "ready",
                    source_clause(),
                    visible_image_clause(Image.id),
                )
                .limit(1)
            )
        return "available" if ready else "empty_dataset"

    async def metadata_ids(self, filters, index_id, limit):
        statement = (
            select(Image.id)
            .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
            .join(ImageEmbedding, ImageEmbedding.image_id == Image.id)
            .where(
                Image.status == "available",
                ImageEmbedding.index_id == index_id,
                ImageEmbedding.status == "ready",
                source_clause(),
                visible_image_clause(Image.id),
            )
        )
        for field in ["source_dataset", "city"]:
            if getattr(filters, field) is not None:
                statement = statement.where(
                    getattr(ImageMetadata, field).is_(None)
                    if field == "source_dataset" and filters.source_dataset == "__unassigned__"
                    else getattr(ImageMetadata, field) == getattr(filters, field)
                )
        if filters.image_ids is not None:
            statement = statement.where(Image.id.in_(filters.image_ids))
        if filters.media_types:
            statement = statement.where(Image.media_type.in_(filters.media_types))
        for field in ["width", "height"]:
            low, high = getattr(filters, "min_" + field), getattr(filters, "max_" + field)
            if low is not None:
                statement = statement.where(getattr(Image, field) >= low)
            if high is not None:
                statement = statement.where(getattr(Image, field) <= high)
        if filters.captured_from:
            statement = statement.where(ImageMetadata.captured_at >= filters.captured_from)
        if filters.captured_to:
            statement = statement.where(ImageMetadata.captured_at <= filters.captured_to)
        for tag in filters.tags_all:
            statement = statement.where(
                exists(
                    select(ImageTag.image_id).where(
                        ImageTag.image_id == Image.id, ImageTag.tag == tag
                    )
                )
            )
        if filters.tags_any:
            statement = statement.where(
                exists(
                    select(ImageTag.image_id).where(
                        ImageTag.image_id == Image.id, ImageTag.tag.in_(filters.tags_any)
                    )
                )
            )
        async with self.services.database.sessions() as session:
            return list((await session.scalars(statement.order_by(Image.id).limit(limit))).all())

    async def validate_evidence(self, entities, relations, associations):
        async with self.services.database.sessions() as session:
            rows = list(
                (
                    await session.scalars(
                        select(Entity).where(
                            Entity.id.in_([e.entity_id for e in entities]), *self.entity_filter()
                        )
                    )
                ).all()
            )
            by_id = {r.id: r for r in rows}
            if any(
                e.entity_id not in by_id or self.record(by_id[e.entity_id]) != e for e in entities
            ):
                return False
            rows = list(
                (
                    await session.scalars(
                        select(EntityRelationship).where(
                            EntityRelationship.id.in_([r.evidence_id for r in relations]),
                            relation_clause(EntityRelationship.id),
                        )
                    )
                ).all()
            )
            by_id = {r.id: r for r in rows}
            for relation in relations:
                current = by_id.get(relation.evidence_id)
                if (
                    current is None
                    or current.verified_at is None
                    or not relation.verified
                    or (
                        not self.allow_fixtures
                        and (
                            current.evidence.get("fixture")
                            or current.source_ref.startswith("fixture:")
                        )
                    )
                    or relation.provenance
                    != {**current.evidence, "verified_at": current.verified_at.isoformat()}
                    or (
                        current.subject_id,
                        current.predicate,
                        current.object_id,
                        current.source_ref,
                    )
                    != (
                        relation.subject_id,
                        relation.predicate,
                        relation.object_id,
                        relation.source_ref,
                    )
                ):
                    return False
            if associations:
                rows = list(
                    (
                        await session.scalars(
                            select(ImageEntity).where(
                                ImageEntity.image_id.in_([r.image_id for r in associations]),
                                ImageEntity.verified.is_(True),
                                ImageEntity.image_id.in_(
                                    select(Image.id)
                                    .outerjoin(ImageMetadata, ImageMetadata.image_id == Image.id)
                                    .where(
                                        source_clause(),
                                        visible_image_clause(Image.id),
                                        Image.status == "available",
                                    )
                                ),
                            )
                        )
                    ).all()
                )
                valid = {(r.image_id, r.entity_id, r.relation, r.source_ref) for r in rows}
                if any(
                    (r.image_id, r.entity_id, r.relation, r.source_ref) not in valid
                    or not r.verified
                    or (not self.allow_fixtures and r.source_ref.startswith("fixture:"))
                    for r in associations
                ):
                    return False
        return True
