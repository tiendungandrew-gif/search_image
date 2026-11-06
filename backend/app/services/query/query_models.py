from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.constraints import ConstraintSpec


class QueryAnalysis(BaseModel):
    original_query: str
    query_type: Literal[
        "SINGLE_INTENT",
        "MULTI_INTENT",
        "IMAGE_SIMILARITY",
        "TEXT_IMAGE",
        "UNSUPPORTED_RELATIONAL_QUERY",
    ]
    language: Literal["vi", "en", "und"]
    constraints: ConstraintSpec | None = None
    logical_operator: str | None = None
    retrieval_strategy: str
    requires_agent: bool = False
    uncertain: bool = False
    limitations: list[str] = Field(default_factory=list)
