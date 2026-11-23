from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.health import Capabilities


class DatasetSnapshot(BaseModel):
    state: Literal["empty_dataset", "index_building", "index_not_ready", "ready", "unavailable"]
    images: int | None = Field(ge=0)
    available_images: int | None = Field(ge=0)
    indexed_images: int | None = Field(ge=0)
    vectors: int | None = Field(ge=0)
    index_id: UUID | None
    index_status: str | None
    generation: int | None = Field(ge=1)


class RagAvailability(BaseModel):
    enabled: bool
    configured: bool
    streaming: bool


class AgentAvailability(BaseModel):
    enabled: bool
    llm_planning: bool


class WorkspaceLimits(BaseModel):
    top_k: int = Field(ge=1, le=50)
    image_bytes: int = Field(ge=1, le=20 * 1024**2)


class WorkspaceSnapshot(BaseModel):
    public_datasets: list[dict[str, str]] = Field(default_factory=list)
    dataset: DatasetSnapshot
    dependencies: dict[str, Literal["healthy", "unhealthy", "timeout"]]
    capabilities: Capabilities
    rag: RagAvailability
    agent: AgentAvailability
    limits: WorkspaceLimits


class EvaluationExperiment(BaseModel):
    id: str
    phase: str
    kind: Literal["retrieval", "agent", "rag"]
    status: str
    attempted: int | None = Field(ge=0)
    successful: int | None = Field(ge=0)
    failed: int | None = Field(ge=0)
    p90_ms: float | None = Field(ge=0, allow_inf_nan=False)
    p95_ms: float | None = Field(ge=0, allow_inf_nan=False)
    recall_at_10: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    quality_status: Literal["not_published"]


class EvaluationSummary(BaseModel):
    state: Literal["available", "empty", "not_available"]
    experiments: list[EvaluationExperiment] = Field(max_length=200)
    skipped: int = Field(ge=0)
