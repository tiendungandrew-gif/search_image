from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.foundation import Timestamps


class ImageTag(Base):
    __tablename__ = "image_tags"
    __table_args__ = (
        CheckConstraint(
            "char_length(tag) BETWEEN 1 AND 64 AND tag = lower(trim(tag))", name="normalized_tag"
        ),
        Index("ix_image_tags_tag_image", "tag", "image_id"),
    )
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id"), primary_key=True)
    tag: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, default="provided")
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageObject(Base):
    __tablename__ = "image_objects"
    __table_args__ = (
        UniqueConstraint("bucket", "object_key"),
        UniqueConstraint("image_id", "role", "derivative_version"),
        CheckConstraint("role IN ('original','thumbnail')", name="role"),
        CheckConstraint("byte_size > 0", name="size"),
        Index("ix_image_objects_image_id", "image_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id"))
    role: Mapped[str] = mapped_column(Text)
    derivative_version: Mapped[str] = mapped_column(Text)
    bucket: Mapped[str] = mapped_column(Text)
    object_key: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    media_type: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','ready','failed','deleting')", name="status"
        ),
        CheckConstraint(
            "status != 'ready' OR (vector_sha256 IS NOT NULL AND verified_at IS NOT NULL)",
            name="ready_receipt",
        ),
        Index("ix_image_embeddings_index_status_image", "index_id", "status", "image_id"),
    )
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id"), primary_key=True)
    index_id: Mapped[UUID] = mapped_column(ForeignKey("search_indexes.id"), primary_key=True)
    status: Mapped[str] = mapped_column(Text, default="pending")
    source_sha256: Mapped[str] = mapped_column(CHAR(64))
    metadata_revision: Mapped[int] = mapped_column(BigInteger)
    vector_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class JobItem(Timestamps, Base):
    __tablename__ = "indexing_job_items"
    __table_args__ = (
        UniqueConstraint("job_id", "source_identity"),
        CheckConstraint(
            "status IN ('awaiting_input','queued','processing','retry_wait','succeeded','failed')",
            name="status",
        ),
        CheckConstraint(
            "stage IN ('validate','deduplicate','preprocess','embed','metadata',"
            "'object','vector','verify','delete')",
            name="stage",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count"),
        CheckConstraint(
            "status != 'processing' OR (claim_token IS NOT NULL "
            "AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="claim",
        ),
        Index("ix_items_due", "status", "next_attempt_at", "created_at", "id"),
        Index("ix_items_job", "job_id"),
        Index("ix_items_index", "index_id"),
        Index("ix_items_image", "image_id"),
        Index("ix_items_expired", "lease_expires_at", postgresql_where=text("status='processing'")),
        Index(
            "uq_items_live",
            "image_id",
            "index_id",
            unique=True,
            postgresql_where=text(
                "status IN ('queued','processing','retry_wait') AND index_id IS NOT NULL"
            ),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("indexing_jobs.id"))
    image_id: Mapped[UUID | None] = mapped_column(ForeignKey("images.id"))
    index_id: Mapped[UUID | None] = mapped_column(ForeignKey("search_indexes.id"))
    source_identity: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(Text, default="queued")
    stage: Mapped[str] = mapped_column(Text, default="validate")
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_token: Mapped[UUID | None] = mapped_column()
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(Text)


class JobAttempt(Base):
    __tablename__ = "job_item_attempts"
    __table_args__ = (
        UniqueConstraint("claim_token"),
        CheckConstraint("attempt_no > 0", name="attempt"),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('succeeded','transient_failure',"
            "'permanent_failure','lease_lost','timeout')",
            name="outcome",
        ),
        Index("ix_attempts_started", "started_at"),
    )
    item_id: Mapped[UUID] = mapped_column(ForeignKey("indexing_job_items.id"), primary_key=True)
    attempt_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_token: Mapped[UUID] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        CheckConstraint("status IN ('processing','completed')", name="status"),
        Index("ix_idempotency_expires", "expires_at"),
    )
    principal_id: Mapped[str] = mapped_column(Text, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    request_sha256: Mapped[str] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_ref: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActiveSearchIndex(Base):
    __tablename__ = "active_search_index"
    __table_args__ = (
        CheckConstraint("corpus_key='default'", name="corpus"),
        CheckConstraint("generation > 0", name="generation"),
        Index("ix_active_search_index_index", "index_id"),
    )
    corpus_key: Mapped[str] = mapped_column(Text, primary_key=True)
    index_id: Mapped[UUID] = mapped_column(ForeignKey("search_indexes.id"))
    generation: Mapped[int] = mapped_column(BigInteger)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
