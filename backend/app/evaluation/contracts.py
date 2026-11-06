from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.search import SearchRequest


class QueryCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: str = Field(min_length=1, max_length=100)
    query_type: Literal["single_intent", "multi_intent", "image", "multimodal"]
    language: Literal["en", "vi", "und"]
    group_id: str = Field(min_length=1, max_length=100)
    split: Literal["dev", "test"]
    request: dict
    image_file: str | None = None
    task: Literal["semantic_relevance", "exact_identity"] = "semantic_relevance"

    @model_validator(mode="after")
    def valid_request(self):
        SearchRequest.model_validate(self.request)
        if self.query_type in {"image", "multimodal"} and not (
            self.image_file or self.request.get("image_id")
        ):
            raise ValueError("reference_required")
        if self.task == "exact_identity" and self.query_type != "image":
            raise ValueError("identity_task_requires_image")
        return self


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(default="fast", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    profile: Literal["fast", "image", "advanced", "mixed"] = "fast"
    requests: int = Field(default=500, ge=1, le=10000)
    concurrency: int = Field(default=1, ge=1, le=20)
    warmup: int = Field(default=10, ge=0, le=200)
    rate: float | None = Field(default=None, gt=0, le=100, allow_inf_nan=False)
    duration: float | None = Field(default=None, gt=0, le=300, allow_inf_nan=False)
    client_timeout: float = Field(default=5, gt=0, le=30)
    seed: int = 42
    top_k: int = Field(default=10, ge=1, le=50)
    candidate_count: int = Field(default=50, ge=1, le=1000)
    rerank: bool = False
    fusion: Literal["rrf", "weighted_score"] = "rrf"
    strategy: Literal["whole_query", "multi_query", "fused"] = "fused"
    filters: dict = Field(default_factory=dict)
    sample_resources: bool = False
    query_types: list[Literal["single_intent", "multi_intent", "image", "multimodal"]] = Field(
        default_factory=list
    )
    paired_text_only: bool = False

    @model_validator(mode="after")
    def budgets(self):
        if self.candidate_count < self.top_k:
            raise ValueError("candidate_count_below_k")
        return self
