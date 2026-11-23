from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.search import ResultMetadata, SearchRequest, normalize_text


class RagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(default=None, max_length=2000)
    question: str | None = Field(default=None, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)
    search_mode: Literal["semantic", "text", "auto", "multi_intent"] = "semantic"
    language: Literal["auto", "vi", "en"] = "auto"
    search: SearchRequest | None = None
    image_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=50)
    expected_index_id: UUID | None = None
    max_evidence_items: int | None = Field(default=None, ge=1, le=10)
    max_context_tokens: int | None = Field(default=None, ge=128, le=8192)
    context_policy: Literal["rank", "descriptive_first"] = "descriptive_first"
    context_format: Literal["full", "compact"] = "full"

    @field_validator("query", "question")
    @classmethod
    def normalized(cls, value):
        return normalize_text(value) if value is not None else value

    @model_validator(mode="after")
    def operation(self):
        if sum([self.query is not None, self.search is not None, self.image_ids is not None]) != 1:
            raise ValueError("choose_query_search_or_existing_image_ids")
        if self.image_ids and len(set(self.image_ids)) != len(self.image_ids):
            raise ValueError("duplicate_image_ids")
        if self.search and (self.search.explain.enabled or self.search.mode == "agent"):
            raise ValueError("recursive_explanation_and_agents_not_supported")
        return self


class RagImage(BaseModel):
    image_id: UUID
    rank: int
    score: float | None = Field(default=None, allow_inf_nan=False)
    score_type: str | None = None
    image_url: str
    thumbnail_url: str
    metadata: ResultMetadata
    constraint_assessments: list = Field(default_factory=list)


class ImageEvidence(BaseModel):
    image_id: UUID
    retrieval_rank: int
    retrieval_score: float | None = Field(default=None, allow_inf_nan=False)
    caption: str | None
    tags: list[str]
    metadata: dict
    evidence_source: str = "postgresql_ready_receipt+qdrant_payload+minio_stat"
    provenance: dict
    incomplete: bool


class Fact(BaseModel):
    fact_id: str
    image_id: UUID
    evidence_field: str
    quote: str
    provenance: dict


class Citation(Fact):
    support_check: Literal["exact_metadata_value"] = "exact_metadata_value"


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fact_ids: list[str] = Field(max_length=12)


class RagAnswer(BaseModel):
    answer: str
    grounding_status: Literal[
        "supported", "partially_supported", "insufficient_evidence", "generation_unavailable"
    ]
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[ImageEvidence] = Field(default_factory=list)
    language: Literal["vi", "en"]
    generated: bool = False
    provider: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    returned_model: str | None = None
    prompt_version: str = "extractive-facts-v1"
    prompt_sha256: str | None = None
    context: dict = Field(default_factory=dict)
    generation_config: dict = Field(default_factory=dict)
    usage: dict | None = None
    error_code: str | None = None
    limitations: list[str] = Field(default_factory=list)


class RagResponse(BaseModel):
    query_id: UUID
    request_id: UUID
    operation: Literal["search_and_explain", "explain_existing"]
    index_id: UUID
    model_id: UUID
    results: list[RagImage]
    rag: RagAnswer
    latency: dict
    warnings: list[dict] = Field(default_factory=list)
