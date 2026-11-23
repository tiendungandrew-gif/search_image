from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.search_text import SEARCH_DOCUMENT_V1


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Image(Timestamps, Base):
    __tablename__ = "images"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_upload','pending','available','deleting','deleted','failed')",
            name="status",
        ),
        CheckConstraint("sha256 IS NOT NULL OR status = 'deleted'", name="hash_required"),
        CheckConstraint("sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'", name="sha256"),
        CheckConstraint(
            "status NOT IN ('deleting','deleted') OR deleted_at IS NOT NULL",
            name="deletion_timestamp",
        ),
        CheckConstraint("media_type IN ('image/jpeg','image/png','image/webp')", name="media_type"),
        CheckConstraint("byte_size > 0 AND width > 0 AND height > 0", name="positive_dimensions"),
        CheckConstraint("metadata_revision > 0", name="metadata_revision"),
        Index(
            "uq_images_sha256", "sha256", unique=True, postgresql_where=text("sha256 IS NOT NULL")
        ),
        Index("ix_images_status_created_id", "status", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sha256: Mapped[str | None] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(Text, server_default="pending_upload")
    media_type: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    metadata_revision: Mapped[int] = mapped_column(BigInteger, server_default="1")
    created_by: Mapped[str] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImageMetadata(Base):
    __tablename__ = "image_metadata"
    __table_args__ = (
        CheckConstraint("title IS NULL OR char_length(title) <= 256", name="title_length"),
        CheckConstraint(
            "description IS NULL OR char_length(description) <= 4000", name="description_length"
        ),
        Index("ix_image_metadata_city", "city"),
        Index("ix_image_metadata_source_dataset", "source_dataset"),
        Index("ix_image_metadata_captured_at", "captured_at"),
        Index("ix_image_metadata_search_document", "search_document", postgresql_using="gin"),
    )
    image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="RESTRICT"), primary_key=True
    )
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    caption_source: Mapped[str | None] = mapped_column(Text)
    source_dataset: Mapped[str | None] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    rights_ref: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    country_code: Mapped[str | None] = mapped_column(CHAR(2))
    city: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    search_document: Mapped[str] = mapped_column(
        TSVECTOR, Computed(SEARCH_DOCUMENT_V1, persisted=True)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmbeddingModel(Base):
    __tablename__ = "embedding_models"
    __table_args__ = (
        CheckConstraint("dimension > 0", name="dimension"),
        CheckConstraint("normalization = 'l2'", name="normalization"),
        CheckConstraint("distance_metric = 'cosine'", name="distance_metric"),
        CheckConstraint("manifest_sha256 ~ '^[0-9a-f]{64}$'", name="manifest_sha256"),
        UniqueConstraint("manifest_sha256"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_name: Mapped[str] = mapped_column(Text)
    model_revision: Mapped[str] = mapped_column(Text)
    processor_revision: Mapped[str] = mapped_column(Text)
    dimension: Mapped[int] = mapped_column(Integer)
    precision: Mapped[str] = mapped_column(Text)
    normalization: Mapped[str] = mapped_column(Text)
    distance_metric: Mapped[str] = mapped_column(Text)
    manifest: Mapped[dict] = mapped_column(JSONB)
    manifest_sha256: Mapped[str] = mapped_column(CHAR(64))
    license_ref: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchIndex(Base):
    __tablename__ = "search_indexes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('building','validating','ready','retired','failed','deleting')",
            name="status",
        ),
        CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'", name="config_sha256"),
        UniqueConstraint("collection_name"),
        Index("ix_search_indexes_model_status", "model_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_id: Mapped[UUID] = mapped_column(ForeignKey("embedding_models.id", ondelete="RESTRICT"))
    collection_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="building")
    config: Mapped[dict] = mapped_column(JSONB)
    config_sha256: Mapped[str] = mapped_column(CHAR(64))
    corpus_snapshot_ref: Mapped[str] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retire_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatasetSource(Base):
    __tablename__ = "dataset_sources"
    __table_args__ = (
        CheckConstraint("kind IN ('local_manifest','object_manifest')", name="kind"),
        CheckConstraint("manifest_sha256 ~ '^[0-9a-f]{64}$'", name="manifest_sha256"),
        UniqueConstraint("name"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    root_config_key: Mapped[str] = mapped_column(Text)
    manifest_ref: Mapped[str] = mapped_column(Text)
    manifest_sha256: Mapped[str] = mapped_column(CHAR(64))
    rights_ref: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IndexingJob(Timestamps, Base):
    __tablename__ = "indexing_jobs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('ingest_upload','ingest_dataset','reindex','delete','retry')", name="kind"
        ),
        CheckConstraint(
            "status IN ('awaiting_input','queued','running','succeeded','partial_failed','failed')",
            name="status",
        ),
        CheckConstraint("total_items >= 0", name="total_items"),
        CheckConstraint(
            "kind NOT IN ('ingest_upload','ingest_dataset','reindex') "
            "OR target_index_id IS NOT NULL",
            name="target_required",
        ),
        CheckConstraint(
            "kind != 'ingest_dataset' OR source_id IS NOT NULL", name="source_required"
        ),
        CheckConstraint("kind != 'retry' OR retry_of IS NOT NULL", name="retry_required"),
        Index("ix_indexing_jobs_status_created_id", "status", "created_at", "id"),
        Index("ix_indexing_jobs_creator_created_id", "created_by", "created_at", "id"),
        Index("ix_indexing_jobs_source_id", "source_id"),
        Index("ix_indexing_jobs_target_index_id", "target_index_id"),
        Index("ix_indexing_jobs_retry_of", "retry_of"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="queued")
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("dataset_sources.id", ondelete="RESTRICT")
    )
    target_index_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("search_indexes.id", ondelete="RESTRICT")
    )
    retry_of: Mapped[UUID | None] = mapped_column(
        ForeignKey("indexing_jobs.id", ondelete="RESTRICT")
    )
    created_by: Mapped[str] = mapped_column(Text)
    request_id: Mapped[UUID] = mapped_column()
    total_items: Mapped[int] = mapped_column(Integer, server_default="0")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_manifest_sha256: Mapped[str | None] = mapped_column(CHAR(64))
