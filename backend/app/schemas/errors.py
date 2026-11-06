from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: str
    reason: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: list[FieldError] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    error: ErrorPayload
