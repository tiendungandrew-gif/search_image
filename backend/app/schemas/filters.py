import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_dataset: str | None = Field(default=None, min_length=1, max_length=128)
    image_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=1000)
    media_types: list[Literal["image/jpeg", "image/png", "image/webp"]] | None = Field(
        default=None, min_length=1, max_length=3
    )
    tags_any: list[str] = Field(default_factory=list, max_length=20)
    tags_all: list[str] = Field(default_factory=list, max_length=20)
    city: str | None = Field(default=None, min_length=1, max_length=128)
    min_width: int | None = Field(default=None, gt=0)
    max_width: int | None = Field(default=None, gt=0)
    min_height: int | None = Field(default=None, gt=0)
    max_height: int | None = Field(default=None, gt=0)
    captured_from: AwareDatetime | None = None
    captured_to: AwareDatetime | None = None

    @field_validator("source_dataset", "city")
    @classmethod
    def metadata_text(cls, value):
        if value is None:
            return None
        if any(unicodedata.category(char) in {"Cc", "Cs"} for char in value):
            raise ValueError("invalid_filter_character")
        value = unicodedata.normalize("NFC", value).strip()
        if not value:
            raise ValueError("empty_filter")
        return value

    @field_validator("tags_any", "tags_all")
    @classmethod
    def tags(cls, values):
        if any(unicodedata.category(char) in {"Cc", "Cs"} for tag in values for char in tag):
            raise ValueError("invalid_filter_character")
        values = sorted({unicodedata.normalize("NFC", v).strip().lower() for v in values})
        if any(not 1 <= len(v) <= 64 for v in values):
            raise ValueError("tag_length")
        return values

    @model_validator(mode="after")
    def ranges(self):
        for low, high in [
            ("min_width", "max_width"),
            ("min_height", "max_height"),
            ("captured_from", "captured_to"),
        ]:
            a, b = getattr(self, low), getattr(self, high)
            if a is not None and b is not None and a > b:
                raise ValueError("reversed_range")
        return self
