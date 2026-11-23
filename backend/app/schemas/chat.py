from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StartConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID


class ReadMessages(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: int = Field(ge=1, le=9223372036854775807)
