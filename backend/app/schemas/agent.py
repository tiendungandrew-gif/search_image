"""Bounded public requests, plans, references and outputs for optional agent workflows."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.filters import Filters
from app.schemas.rag import RagAnswer, RagImage
from app.schemas.search import OptionalFeature, normalize_text

EntityType = Literal[
    "city",
    "landmark",
    "country",
    "location",
    "person",
    "object",
    "organization",
    "category",
    "other",
]
Predicate = Literal[
    "located_in", "contains", "part_of", "has_landmark", "depicts", "related_to", "associated_with"
]
ExecutionStatus = Literal[
    "planned",
    "running",
    "completed",
    "partial",
    "insufficient_evidence",
    "timeout",
    "failed",
    "cancelled",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentBudgets(StrictModel):
    max_hops: int = Field(default=3, ge=1, le=3)
    max_tool_calls: int = Field(default=6, ge=1, le=6)
    max_output_tokens: int = Field(default=512, ge=16, le=512)
    deadline_ms: int = Field(default=15000, ge=100, le=30000)


class AgentRequest(StrictModel):
    query: str | None = Field(default=None, max_length=2000)
    text: str | None = Field(default=None, max_length=2000)
    mode: Literal["agent", "auto", "text", "multi_intent", "multimodal", "metadata", "explain"] = (
        "agent"
    )
    search_mode: Literal["agent"] | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    image_id: UUID | None = None
    image_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=50)
    filters: Filters = Field(default_factory=Filters)
    max_hops: int | None = Field(default=None, ge=1, le=3)
    budgets: AgentBudgets = Field(default_factory=AgentBudgets)
    include_explanation: bool = False
    explain: OptionalFeature | None = None
    allow_fallback: bool = False
    language: Literal["auto", "vi", "en"] = "auto"
    planning_mode: Literal["deterministic", "llm"] | None = None
    rerank: bool = False

    @model_validator(mode="after")
    def aliases(self):
        if (self.query is None) == (self.text is None):
            raise ValueError("choose_one_query_or_text")
        self.query = normalize_text(self.query if self.query is not None else self.text)
        if self.search_mode and self.mode != "agent":
            raise ValueError("ambiguous_agent_mode")
        if self.max_hops:
            self.budgets.max_hops = min(self.budgets.max_hops, self.max_hops)
        if self.explain is not None:
            self.include_explanation = self.explain.enabled
        if self.mode == "multimodal" and self.image_id is None:
            raise ValueError("image_id_required")
        if self.mode == "explain" and not self.image_ids:
            raise ValueError("image_ids_required")
        if self.mode == "explain":
            self.include_explanation = True
        return self


class StateReference(StrictModel):
    step_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
    field: Literal["entity_ids", "image_ids"]


IdInput = Annotated[list[UUID], Field(min_length=1, max_length=1000)] | StateReference


class AgentPlanStep(StrictModel):
    step_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
    tool_name: str = Field(min_length=1, max_length=64)
    arguments: dict = Field(default_factory=dict, max_length=16)
    depends_on: list[str] = Field(default_factory=list, max_length=6)


class AgentPlan(StrictModel):
    plan_id: UUID = Field(default_factory=uuid4)
    original_query: str = Field(min_length=1, max_length=2000)
    steps: list[AgentPlanStep] = Field(min_length=1, max_length=6)
    max_hops: int = Field(default=3, ge=1, le=3)


class EntityRecord(StrictModel):
    entity_id: UUID
    canonical_name: str
    entity_type: EntityType
    source_ref: str
    provenance: dict
    fixture: bool = False


class KnowledgeEvidence(StrictModel):
    evidence_id: UUID
    subject_id: UUID
    predicate: Predicate
    object_id: UUID
    source_ref: str
    verified: bool
    provenance: dict


class ImageAssociation(StrictModel):
    image_id: UUID
    entity_id: UUID
    relation: Literal["depicts", "located_in", "associated_with"]
    source_ref: str
    verified: bool


class ToolOutput(StrictModel):
    entity_ids: list[UUID] = Field(default_factory=list, max_length=50)
    image_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    entities: list[EntityRecord] = Field(default_factory=list, max_length=50)
    relations: list[KnowledgeEvidence] = Field(default_factory=list, max_length=100)
    associations: list[ImageAssociation] = Field(default_factory=list, max_length=1000)
    images: list[RagImage] = Field(default_factory=list, max_length=50)
    rag: RagAnswer | None = None
    timing: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    insufficient: bool = False


class StepTrace(StrictModel):
    step_id: str
    tool: str
    status: str
    duration_ms: float
    logical_hop: int
    result_count: int = 0
    error_code: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class PlanningAttemptTrace(StrictModel):
    attempt: int = Field(ge=1, le=2)
    status: Literal["running", "completed", "failed", "timeout", "cancelled"]
    duration_ms: float = Field(default=0, ge=0)
    error_code: str | None = None
    input_bytes: int = Field(default=0, ge=0)


class AgentResponse(StrictModel):
    query_id: UUID
    request_id: str
    execution_id: UUID
    index_id: UUID | None = None
    model_id: UUID | None = None
    manifest_sha256: str | None = None
    service_class: str = "augmented"
    requested_mode: str = "agent"
    search_mode: str
    status: ExecutionStatus
    query_success: bool
    dataset_status: Literal["available", "empty_dataset", "search_unavailable", "unknown"]
    results: list[RagImage]
    resolved_entities: list[EntityRecord]
    steps: list[StepTrace]
    evidence: list[KnowledgeEvidence]
    image_associations: list[ImageAssociation]
    image_sources: dict[str, list[str]] = Field(default_factory=dict)
    answer: str | None = None
    rag: RagAnswer | None = None
    relationship_summary: str | None = None
    planner_mode: str
    planner_attempts: int
    plan_validated: bool = False
    planner_version: str = "agent-template-plan-v2"
    planner_trace: list[PlanningAttemptTrace] = Field(default_factory=list, max_length=2)
    planner_usage: list[dict] = Field(default_factory=list)
    planner_model_id: str | None = None
    planner_prompt_sha256: str | None = None
    plan_id: UUID | None = None
    logical_hops: int
    tool_calls: int
    latency_ms: float
    latency: dict
    warnings: list[str]
    error_code: str | None = None
    verification_state: Literal["VERIFIED_WITH_REAL_DATA", "NOT_VERIFIED", "TESTED_WITH_MOCKS"]
