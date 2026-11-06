from typing import Literal

from pydantic import BaseModel, ConfigDict


class Capabilities(BaseModel):
    text_search: bool = False
    image_search: bool = False
    multimodal: bool = False
    multi_intent: bool = False
    rerank: bool = False
    explanations: bool = False
    agent: bool = False


class WorkerState(BaseModel):
    state: Literal["unknown", "fresh", "stale"] = "unknown"


class HealthSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok", "not_ready"]
    check: Literal["live", "ingest", "search"]
    capabilities: Capabilities
    worker: WorkerState
    dependencies: dict[str, str] | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, Literal["healthy", "unhealthy", "timeout"]]


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"
    service: str


class SystemInfo(BaseModel):
    app_name: str
    app_version: str
    environment: str
    api_version: str = "v1"
