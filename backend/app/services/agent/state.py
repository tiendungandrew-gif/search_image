from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4

from app.schemas.agent import AgentPlan, AgentRequest, PlanningAttemptTrace, StepTrace, ToolOutput
from app.services.agent.errors import AgentError


@dataclass
class AgentState:
    request: AgentRequest
    request_id: str
    deadline: float
    max_calls: int
    max_hops: int
    execution_id: object = field(default_factory=uuid4)
    query_id: object = field(default_factory=uuid4)
    status: str = "planned"
    plan: AgentPlan | None = None
    outputs: dict[str, ToolOutput] = field(default_factory=dict)
    traces: list[StepTrace] = field(default_factory=list)
    fingerprints: set[str] = field(default_factory=set)
    tool_calls: int = 0
    logical_hops: int = 0
    planner_attempts: int = 0
    planner_trace: list[PlanningAttemptTrace] = field(default_factory=list)
    planner_input_bytes: int = 0
    require_entity_links: bool = False
    started_at: float = field(default_factory=perf_counter)
    plan_validated: bool = False
    planner_usage: list[dict] = field(default_factory=list)
    planner_model_id: str | None = None
    planner_prompt_sha256: str | None = None
    warnings: list[str] = field(default_factory=list)

    def remaining(self):
        remaining = self.deadline - perf_counter()
        if remaining <= 0:
            raise AgentError("AGENT_DEADLINE_EXCEEDED", "timeout")
        return remaining

    def transition(self, status):
        allowed = {
            "planned": {"running", "failed", "cancelled", "insufficient_evidence", "timeout"},
            "running": {
                "completed",
                "partial",
                "insufficient_evidence",
                "timeout",
                "failed",
                "cancelled",
            },
        }
        if status not in allowed.get(self.status, set()):
            raise AgentError("INVALID_STATE_TRANSITION")
        self.status = status
