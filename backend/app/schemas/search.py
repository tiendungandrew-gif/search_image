import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.constraints import ConstraintSpec, validate_tree
from app.schemas.filters import Filters


def normalize_text(value: str) -> str:
    if any(unicodedata.category(c) in {"Cc", "Cs"} and not c.isspace() for c in value):
        raise ValueError("invalid_control_character")
    value = " ".join(unicodedata.normalize("NFC", value).split())
    if not value:
        raise ValueError("empty_query")
    return value


class OptionalFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    on_failure: Literal["error", "skip", "omit"] = "error"


class RerankOptions(OptionalFeature):
    candidate_limit: int | None = Field(default=None, ge=1, le=100)
    timeout_ms: int | None = Field(default=None, ge=1, le=1000)


class FusionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method: Literal["rrf", "weighted_rrf", "weighted_score"] = "rrf"
    text_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    image_weight: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    rrf_k: int = Field(default=60, ge=1, le=1000)

    @model_validator(mode="after")
    def weights(self):
        if self.text_weight + self.image_weight <= 0:
            raise ValueError("fusion_weights_all_zero")
        return self


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str | None = Field(default=None, max_length=2000)
    query: str | None = Field(default=None, max_length=2000)
    mode: Literal["auto", "text", "image", "multi_intent", "multimodal", "agent"] = "auto"
    search_mode: (
        Literal[
            "semantic", "image_similarity", "text", "image", "auto", "multi_intent", "multimodal"
        ]
        | None
    ) = None
    image_id: UUID | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    candidate_count: int | None = Field(default=None, ge=1, le=1000)
    filters: Filters = Field(default_factory=Filters)
    exclude_self: bool = True
    rerank: RerankOptions = Field(default_factory=RerankOptions)
    explain: OptionalFeature = Field(default_factory=OptionalFeature)
    constraints: ConstraintSpec | None = None
    require_verified: bool = False
    fusion: FusionOptions | None = None
    fusion_strategy: Literal["rrf", "weighted_rrf", "weighted_score"] | None = None
    text_weight: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    image_weight: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    retrieval_strategy: Literal["whole_query", "multi_query", "fused"] = "fused"

    @field_validator("rerank", mode="before")
    @classmethod
    def rerank_alias(cls, value):
        return {"enabled": value} if isinstance(value, bool) else value

    @field_validator("image_id", mode="before")
    @classmethod
    def uuid_from_json(cls, value):
        return UUID(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def aliases(self):
        if self.query is not None:
            if self.text is not None:
                raise ValueError("ambiguous_query_alias")
            self.text = self.query
        if self.search_mode:
            mode = {"semantic": "text", "image_similarity": "image"}.get(
                self.search_mode, self.search_mode
            )
            if self.mode not in {"auto", mode}:
                raise ValueError("ambiguous_mode_alias")
            self.mode = mode
        if self.text is not None:
            self.text = normalize_text(self.text)
        if self.candidate_count is not None and self.candidate_count < self.top_k:
            raise ValueError("candidate_count_below_top_k")
        if self.constraints is not None:
            validate_tree(self.constraints)
        flat = any(
            value is not None
            for value in [self.fusion_strategy, self.text_weight, self.image_weight]
        )
        if flat:
            if self.fusion is not None:
                raise ValueError("ambiguous_fusion_alias")
            self.fusion = FusionOptions(
                method=self.fusion_strategy or "rrf",
                text_weight=0.5 if self.text_weight is None else self.text_weight,
                image_weight=0.5 if self.image_weight is None else self.image_weight,
            )
        return self


class ResultMetadata(BaseModel):
    title: str | None
    caption: str | None = None
    width: int
    height: int
    media_type: str
    tags: list[str]
    source_dataset: str | None
    city: str | None
    license: str | None


class SearchResult(BaseModel):
    image_id: UUID
    rank: int
    score: float = Field(allow_inf_nan=False)
    score_type: Literal["cosine", "rrf", "weighted_score", "reranker"] = "cosine"
    ranking_version: str = "cosine-v1"
    image_url: str
    thumbnail_url: str
    metadata: ResultMetadata
    constraint_assessments: list = Field(default_factory=list)
    constraint_evidence: list = Field(default_factory=list)
    score_components: dict = Field(default_factory=dict)
    contributing_branches: list = Field(default_factory=list)


class SearchResponse(BaseModel):
    query_id: UUID
    request_id: UUID
    requested_mode: str
    search_mode: Literal["text", "image", "multi_intent", "multimodal"]
    service_class: Literal["fast", "advanced"] = "fast"
    index_id: UUID
    model_id: UUID
    manifest_sha256: str
    results: list[SearchResult]
    total_results: int
    effective_settings: dict
    latency: dict
    latency_ms: float
    warnings: list[dict] = Field(default_factory=list)
    query_analysis: dict | None = None
    explanation: None = None
    agent: None = None
