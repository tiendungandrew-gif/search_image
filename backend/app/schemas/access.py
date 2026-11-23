"""Public account/admin inputs; password hashes and session secrets never serialize."""

import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name", "name", check_fields=False)
    @classmethod
    def clean_name(cls, value):
        if value is None:
            return value
        if any(unicodedata.category(c) in {"Cc", "Cs"} for c in value) or not value.strip():
            raise ValueError("invalid_name")
        return value.strip()


class LoginInput(StrictInput):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$")
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):
        return value.lower()


class RegistrationInput(LoginInput):
    password: SecretStr = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class CreateUser(RegistrationInput):
    role: Literal["user", "admin"] = "user"


class UpdateUser(StrictInput):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None


class ResetPassword(StrictInput):
    password: SecretStr = Field(min_length=12, max_length=128)


class ChangePassword(ResetPassword):
    current_password: SecretStr = Field(min_length=1, max_length=128)


class DatasetInput(StrictInput):
    key: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$")
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1000)
    shared_with_members: bool = False
    is_public: bool = False


class DatasetUpdate(StrictInput):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1000)
    is_active: bool = True
    shared_with_members: bool = False
    is_public: bool = False


class GrantInput(StrictInput):
    dataset_ids: list[UUID] = Field(max_length=1000)


class ImageEdit(StrictInput):
    title: str | None = Field(default=None, max_length=256)
    caption: str | None = Field(default=None, max_length=4000)
    dataset_id: UUID
    tags: list[str] = Field(default_factory=list, max_length=64)


class IndexCreate(StrictInput):
    version: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$")
    model_id: UUID


class ReindexInput(StrictInput):
    target_index_id: UUID
    dataset_id: UUID | None = None


class IndexAction(StrictInput):
    index_id: UUID


class QuickLoginInput(StrictInput):
    role: Literal["admin", "user"]
