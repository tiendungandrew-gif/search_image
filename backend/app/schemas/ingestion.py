import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ImageMetadataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=4000)
    caption: str | None = Field(default=None, max_length=4000)
    caption_source: str | None = Field(default=None, max_length=160)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source_dataset: str = Field(min_length=1, max_length=128)
    source_uri: str | None = Field(default=None, max_length=2048)
    license: str = Field(min_length=1, max_length=256)
    rights_ref: str = Field(min_length=1, max_length=2048)

    @field_validator(
        "title",
        "description",
        "caption",
        "caption_source",
        "source_dataset",
        "source_uri",
        "license",
        "rights_ref",
    )
    @classmethod
    def validate_stored_text(cls, value):
        if value is not None and any(
            unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\r\t" for char in value
        ):
            raise ValueError("invalid_metadata_character")
        return value

    def fingerprint_data(self):
        values = self.model_dump()
        # Preserve idempotency hashes from before optional caption attribution existed.
        if self.caption_source is None:
            values.pop("caption_source")
        return values

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags):
        if any(unicodedata.category(char) in {"Cc", "Cs"} for tag in tags for char in tag):
            raise ValueError("invalid_tag_character")
        tags = sorted({unicodedata.normalize("NFC", x).strip().lower() for x in tags})
        if any(not 1 <= len(x) <= 64 for x in tags):
            raise ValueError("invalid_tag")
        return tags


class JobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["ingest_dataset", "reindex", "retry", "delete"]
    target_index_id: UUID | None = None
    source_id: UUID | None = None
    image_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=1000)
    retry_of: UUID | None = None
    item_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def check_fields(self):
        expected = {
            "ingest_dataset": {"source_id", "target_index_id"},
            "reindex": {"image_ids", "target_index_id"},
            "retry": {"retry_of", "item_ids"},
            "delete": {"image_ids"},
        }[self.kind]
        supplied = {
            key
            for key in ["source_id", "target_index_id", "image_ids", "retry_of", "item_ids"]
            if getattr(self, key) is not None
        }
        if expected != supplied:
            raise ValueError("kind_fields")
        for key in ["image_ids", "item_ids"]:
            value = getattr(self, key)
            if value and len(value) != len(set(value)):
                raise ValueError("duplicate_ids")
        return self


class UploadResponse(BaseModel):
    image_id: UUID
    duplicate: bool
    job_id: UUID | None
    status: Literal["queued", "available"]
    status_url: str | None


class JobAccepted(BaseModel):
    job_id: UUID
    status: Literal["queued"]
    status_url: str


class JobItemResponse(BaseModel):
    item_id: UUID
    image_id: UUID | None
    index_id: UUID | None
    status: Literal["awaiting_input", "queued", "processing", "retry_wait", "succeeded", "failed"]
    stage: str
    attempt_count: int
    last_error_code: str | None
    next_attempt_at: datetime | None


class JobResponse(BaseModel):
    job_id: UUID
    kind: str
    status: Literal["awaiting_input", "queued", "running", "succeeded", "partial_failed", "failed"]
    target_index_id: UUID | None
    counts: dict[str, int]
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    started_at: datetime | None
    error_summary: dict[str, int]
    items: list[JobItemResponse]
    next_cursor: str | None
