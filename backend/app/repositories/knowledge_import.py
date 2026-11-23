"""Administrative import, never an agent tool. Verified means operator/source attestation."""

import json
import os
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator
from sqlalchemy.engine import make_url

from app.db.models.knowledge import Entity, EntityRelationship, ImageEntity
from app.repositories.knowledge_repository import name_key
from app.schemas.agent import EntityType, Predicate, StrictModel


class EntityInput(StrictModel):
    id: UUID
    canonical_name: str = Field(min_length=1, max_length=256)
    entity_type: EntityType
    locale: str = Field(default="und", min_length=2, max_length=16)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    external_key: str | None = Field(default=None, max_length=256)
    provenance: dict

    @field_validator("provenance")
    @classmethod
    def source(cls, value):
        if (
            not isinstance(value.get("source_ref"), str)
            or not 1 <= len(value["source_ref"]) <= 2000
            or len(json.dumps(value).encode()) > 16384
        ):
            raise ValueError("knowledge_provenance_required")
        return value


class RelationInput(StrictModel):
    id: UUID
    subject_id: UUID
    predicate: Predicate
    object_id: UUID
    source_ref: str = Field(min_length=1, max_length=2000)
    evidence: dict
    verified_at: AwareDatetime | None = None


class ImageEntityInput(StrictModel):
    image_id: UUID
    entity_id: UUID
    relation: str = Field(default="depicts", pattern=r"^(depicts|located_in|associated_with)$")
    source_ref: str = Field(min_length=1, max_length=2000)
    verified: bool = False


class KnowledgeImport(StrictModel):
    entities: list[EntityInput] = Field(default_factory=list, max_length=1000)
    relationships: list[RelationInput] = Field(default_factory=list, max_length=1000)
    image_entities: list[ImageEntityInput] = Field(default_factory=list, max_length=1000)
    fixture: bool = False


def fixture_database_allowed(cfg):
    url = make_url(cfg.database_url.get_secret_value())
    isolated_name = url.database.startswith("agent_test_") or (
        os.getenv("QA_ISOLATED") == "1"
        and url.host == "qa-postgres"
        and url.database.startswith("image_search_qa")
    )
    return cfg.app_env == "test" and cfg.agent_allow_fixture_knowledge and isolated_name


async def import_knowledge(services, data, apply=False, dataset_id=None):
    payload = KnowledgeImport.model_validate(data)
    cfg = services.settings
    fixture = (
        payload.fixture
        or any(
            e.provenance.get("fixture") or e.provenance["source_ref"].startswith("fixture:")
            for e in payload.entities
        )
        or any(
            r.evidence.get("fixture") or r.source_ref.startswith("fixture:")
            for r in payload.relationships
        )
        or any(r.source_ref.startswith("fixture:") for r in payload.image_entities)
    )
    if fixture and not fixture_database_allowed(cfg):
        raise ValueError("FIXTURES_REQUIRE_ISOLATED_AGENT_TEST_DATABASE")
    for entity in payload.entities:
        if any(not isinstance(a, str) or not 1 <= len(a) <= 256 for a in entity.aliases):
            raise ValueError("INVALID_ALIAS")
        if payload.fixture:
            entity.provenance["fixture"] = True
    if not apply:
        return {
            "status": "validated_not_applied",
            "entities": len(payload.entities),
            "relationships": len(payload.relationships),
            "image_entities": len(payload.image_entities),
            "fixture": fixture,
        }
    counts = {"entities": 0, "relationships": 0, "image_entities": 0}
    async with services.database.sessions() as session, session.begin():
        for record in payload.entities:
            values = record.model_dump()
            values["name_key"] = name_key(record.canonical_name)
            values["aliases"] = sorted({name_key(a) for a in record.aliases})
            existing = await session.get(Entity, record.id)
            if existing is None:
                session.add(Entity(**values))
                counts["entities"] += 1
            elif any(getattr(existing, k) != v for k, v in values.items()):
                raise ValueError("ENTITY_IDENTITY_CONFLICT")
        await session.flush()
        for record in payload.relationships:
            if record.subject_id == record.object_id:
                raise ValueError("SELF_RELATIONSHIP")
            values = record.model_dump()
            if payload.fixture:
                values["evidence"] = {**values["evidence"], "fixture": True}
            existing = await session.get(EntityRelationship, record.id)
            if existing is None:
                session.add(EntityRelationship(**values))
                counts["relationships"] += 1
            elif any(getattr(existing, k) != v for k, v in values.items()):
                raise ValueError("RELATION_IDENTITY_CONFLICT")
        for record in payload.image_entities:
            identity = (record.image_id, record.entity_id, record.relation)
            existing = await session.get(ImageEntity, identity)
            values = record.model_dump()
            if existing is None:
                session.add(ImageEntity(**values))
                counts["image_entities"] += 1
            elif any(getattr(existing, k) != v for k, v in values.items()):
                raise ValueError("IMAGE_ASSOCIATION_CONFLICT")
        await session.flush()
        if dataset_id is not None:
            from sqlalchemy.dialects.postgresql import insert

            from app.db.models.access import EntityDataset, RelationDataset

            for entity in payload.entities:
                query = insert(EntityDataset).values(dataset_id=dataset_id, entity_id=entity.id)
                await session.execute(query.on_conflict_do_nothing())
            for relation in payload.relationships:
                query = insert(RelationDataset).values(
                    dataset_id=dataset_id, relation_id=relation.id
                )
                await session.execute(query.on_conflict_do_nothing())
    return {"status": "applied", "inserted": counts, "fixture": fixture}
