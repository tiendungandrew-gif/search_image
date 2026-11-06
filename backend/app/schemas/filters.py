import unicodedata
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_dataset: str | None = Field(default=None, min_length=1, max_length=128)
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

    @field_validator("tags_any", "tags_all")
    @classmethod
    def tags(cls, values):
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
