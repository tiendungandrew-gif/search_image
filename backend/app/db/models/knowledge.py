"""Knowledge records are independent of the active image index; empty tables are valid."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("canonical_name", "entity_type", "locale"),
        UniqueConstraint("external_key"),
        CheckConstraint(
            "entity_type IN ('city','landmark','country','location','person','object',"
            "'organization','category','other')",
            name="entity_type",
        ),
        Index("ix_entities_name_key", "name_key"),
        Index("ix_entities_aliases", "aliases", postgresql_using="gin"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(Text)
    name_key: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(Text, default="und")
    external_key: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    provenance: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint("subject_id", "predicate", "object_id", "source_ref"),
        CheckConstraint(
            "predicate IN ('located_in','contains','part_of','has_landmark',"
            "'depicts','related_to','associated_with')",
            name="predicate",
        ),
        CheckConstraint("subject_id != object_id", name="distinct_entities"),
        Index("ix_relationships_subject_predicate", "subject_id", "predicate"),
        Index("ix_relationships_object_predicate", "object_id", "predicate"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"))
    predicate: Mapped[str] = mapped_column(Text)
    object_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"))
    source_ref: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageEntity(Base):
    __tablename__ = "image_entities"
    __table_args__ = (
        CheckConstraint("relation IN ('depicts','located_in','associated_with')", name="relation"),
        Index("ix_image_entities_entity_relation", "entity_id", "relation", "image_id"),
    )
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id"), primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    relation: Mapped[str] = mapped_column(Text, primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
