"""Synthetic workflow contracts only; none of these are real-world accuracy labels."""

import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.repositories.knowledge_import import import_knowledge
from app.schemas.agent import (
    AgentPlan,
    AgentPlanStep,
    AgentRequest,
    EntityRecord,
    ImageAssociation,
    ToolOutput,
)
from app.schemas.rag import RagImage
from app.schemas.search import ResultMetadata
from app.services.agent.agent_service import AgentService
from app.services.agent.errors import AgentError
from app.services.agent.plan_validator import validate_plan
from app.services.agent.planner import deterministic_plan
from app.services.agent.router import route_query
from app.services.agent.state import AgentState
from app.services.agent.tool_registry import build_registry

IMAGE = UUID("30000000-0000-4000-8000-000000000001")


def image(identity=IMAGE):
    return RagImage(
        image_id=identity,
        rank=1,
        score=0.2,
        score_type="cosine",
        image_url=f"/api/v1/images/{identity}/content?variant=original",
        thumbnail_url=f"/api/v1/images/{identity}/content?variant=thumbnail",
        metadata=ResultMetadata(
            title=None,
            source_dataset="unit-fixture",
            city=None,
            license="fixture",
            width=8,
            height=8,
            media_type="image/png",
            tags=[],
        ),
    )


class FixtureKnowledge:
    def __init__(self, dataset="available", valid=True):
        self.dataset, self.valid = dataset, valid

    async def dataset_status(self, runtime):
        return self.dataset

    async def validate_evidence(self, *args):
        return self.valid


class FixtureTools:
    def __init__(self, fail_at=None, delay=0):
        self.calls = []
        self.fail_at = fail_at
        self.delay = delay
        self.reached = asyncio.Event()

    async def invoke(self, name, args, state, emit):
        self.calls.append((name, args))
        self.reached.set()
        if self.delay:
            await asyncio.sleep(self.delay)
        if name == self.fail_at:
            return ToolOutput(insufficient=True)
        if name == "rag_explain":
            raise AgentError("AGENT_RAG_DISABLED")
        if name in {"entity_lookup", "relationship_lookup", "get_related_entities"}:
            identity = UUID(f"10000000-0000-4000-8000-{len(self.calls):012d}")
            entity = EntityRecord(
                entity_id=identity,
                canonical_name="Fictional unit entity",
                entity_type="city" if name == "relationship_lookup" else "landmark",
                source_ref="fixture://unit",
                provenance={"fixture": True},
                fixture=True,
            )
            return ToolOutput(entity_ids=[identity], entities=[entity])
        return ToolOutput(
            image_ids=[IMAGE],
            images=[image()],
            associations=[
                ImageAssociation(
                    image_id=IMAGE,
                    entity_id=args.entity_ids[0],
                    relation="depicts",
                    source_ref="fixture://unit",
                    verified=True,
                )
            ]
            if getattr(args, "entity_ids", None)
            else [],
        )


@pytest.fixture
def agent_factory(settings, monkeypatch):
    class FixtureEvidence:
        def __init__(self, runtime):
            pass

        async def retrieve(self, ids, retrieved=None):
            kept = [i for i in (retrieved or []) if i.image_id == IMAGE]
            return [], kept, [str(i) for i in ids if i != IMAGE]

    monkeypatch.setattr("app.services.agent.evidence_aggregator.EvidenceRetriever", FixtureEvidence)

    def create(tools=None, knowledge=None, **overrides):
        cfg = settings.model_copy(update={"agent_enabled": True, "app_env": "test", **overrides})
        services = SimpleNamespace(settings=cfg)
        runtime = SimpleNamespace(
            available=True,
            registry=SimpleNamespace(
                index=SimpleNamespace(id=uuid4()),
                model=SimpleNamespace(id=uuid4(), manifest_sha256="a" * 64),
            ),
        )
        return AgentService(
            services,
            runtime,
            None,
            knowledge=knowledge or FixtureKnowledge(),
            tools=tools or FixtureTools(),
        )

    return create


@pytest.mark.parametrize(
    "query,strategy",
    [
        ("Find a red motorcycle.", "semantic"),
        ("a cat and a dog", "multi_intent"),
        ("Find landmarks in the city where Fixture Lake Alpha is located.", "agentic_multi_hop"),
        ("Tìm ảnh địa danh ở thành phố nơi Hồ Hư Cấu tọa lạc.", "agentic_multi_hop"),
        ("What is the city where someone was born?", "unsupported_relation"),
    ],
)
def test_router_finite_patterns_preserve_query(query, strategy):
    request = AgentRequest(query=query)
    assert route_query(request).strategy == strategy
    assert request.query == query


def relational():
    return AgentRequest(query="Find landmarks in the city where Fixture Lake Alpha is located")


def test_registry_has_nine_readonly_typed_tools(settings):
    registry = build_registry()
    assert len(registry) == 9
    assert all(
        d.permission == "search:read" and d.input_model.model_json_schema()
        for d in registry.values()
    )
    assert not {"shell", "sql", "http_get"}.intersection(registry)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("unknown", "UNKNOWN_TOOL"),
        ("arguments", "INVALID_TOOL_ARGUMENTS"),
        ("reference", "UNDECLARED_STATE_REFERENCE"),
        ("hops", "HOP_LIMIT_EXCEEDED"),
        ("budget", "PLAN_BUDGET_OR_QUERY_MISMATCH"),
        ("weaken", "UNSUPPORTED_RELATIONAL_PLAN"),
    ],
)
def test_plans_fail_closed_before_execution(mutation, code):
    request = relational()
    route = route_query(request)
    plan = deterministic_plan(request, route)
    calls, hops = 6, 3
    if mutation == "unknown":
        plan.steps[0].tool_name = "run_shell"
    if mutation == "arguments":
        plan.steps[0].arguments["sql"] = "DELETE FROM images"
    if mutation == "reference":
        plan.steps[1].depends_on = []
    if mutation == "hops":
        hops = 2
    if mutation == "budget":
        calls = 3
    if mutation == "weaken":
        plan.steps[-1].arguments.pop("entity_ids")
    with pytest.raises(AgentError) as error:
        validate_plan(plan, request, route, build_registry(), calls, hops)
    assert error.value.code == code


def test_dag_cycles_and_wrong_reference_types_are_rejected():
    request = relational()
    route = route_query(request)
    plan = AgentPlan(
        original_query=request.query,
        steps=[
            AgentPlanStep(
                step_id="a", tool_name="entity_lookup", arguments={"name": "A"}, depends_on=["b"]
            ),
            AgentPlanStep(
                step_id="b", tool_name="entity_lookup", arguments={"name": "B"}, depends_on=["a"]
            ),
        ],
    )
    with pytest.raises(AgentError, match="CYCLIC_PLAN"):
        validate_plan(plan, request, route, build_registry(), 6, 3)
    plan = deterministic_plan(request, route)
    plan.steps[1].arguments["entity_ids"]["field"] = "image_ids"
    with pytest.raises(AgentError, match="INVALID_REFERENCE_TYPE"):
        validate_plan(plan, request, route, build_registry(), 6, 3)


async def test_dependent_steps_consume_actual_ids_and_deduplicate(agent_factory):
    tools = FixtureTools()
    agent = agent_factory(tools=tools)
    result = await agent.execute(relational(), "unit-request")
    assert result.status == "completed" and result.query_success
    assert result.logical_hops == 3 and result.tool_calls == 4
    assert tools.calls[1][1].entity_ids == [UUID("10000000-0000-4000-8000-000000000001")]
    assert tools.calls[3][1].entity_ids == [UUID("10000000-0000-4000-8000-000000000003")]
    assert len(result.results) == 1 and result.verification_state == "TESTED_WITH_MOCKS"
    assert agent.inflight == 0


@pytest.mark.parametrize(
    "missing,calls",
    [
        ("entity_lookup", 1),
        ("relationship_lookup", 2),
        ("get_related_entities", 3),
        ("semantic_image_search", 4),
    ],
)
async def test_missing_evidence_stops_dependent_steps_without_broad_fallback(
    agent_factory, missing, calls
):
    tools = FixtureTools(fail_at=missing)
    agent = agent_factory(tools=tools)
    result = await agent.execute(relational(), "unit")
    assert (
        result.status == "insufficient_evidence" and not result.results and not result.query_success
    )
    assert len(tools.calls) == calls


async def test_empty_dataset_initializes_plan_but_does_not_invent_results(agent_factory):
    tools = FixtureTools()
    agent = agent_factory(tools=tools, knowledge=FixtureKnowledge("empty_dataset"))
    result = await agent.execute(relational(), "empty")
    assert result.dataset_status == "empty_dataset" and result.plan_id
    assert result.status == "insufficient_evidence" and result.results == [] and not tools.calls


async def test_optional_rag_failure_keeps_real_adapter_results(agent_factory):
    agent = agent_factory()
    result = await agent.execute(AgentRequest(query="a cup", include_explanation=True), "unit")
    assert result.status == "partial" and len(result.results) == 1 and result.answer is None
    assert "AGENT_RAG_DISABLED" in result.warnings


async def test_timeout_and_cancel_release_admission(agent_factory):
    agent = agent_factory(tools=FixtureTools(delay=0.1), agent_tool_timeout_seconds=0.01)
    result = await agent.execute(AgentRequest(query="a cup"), "unit")
    assert (
        result.status == "timeout" and result.error_code == "TOOL_TIMEOUT" and agent.inflight == 0
    )
    tools = FixtureTools(delay=30)
    agent = agent_factory(tools=tools)
    task = asyncio.create_task(agent.execute(AgentRequest(query="a cup"), "cancel"))
    await asyncio.wait_for(tools.reached.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert agent.inflight == 0


async def test_duplicate_tool_call_is_not_executed_twice(agent_factory):
    agent = agent_factory()
    request = AgentRequest(query="a cup")
    state = AgentState(request, "unit", __import__("time").perf_counter() + 2, 6, 3)
    step = AgentPlanStep(step_id="lookup", tool_name="entity_lookup", arguments={"name": "Fixture"})
    definition = agent.registry[step.tool_name]
    args = definition.input_model.model_validate(step.arguments)

    async def emit(*args):
        pass

    await agent.executor.execute(step, definition, args, state, 0, emit)
    with pytest.raises(AgentError, match="LOOP_DETECTED"):
        await agent.executor.execute(step, definition, args, state, 0, emit)
    assert state.tool_calls == 1


async def test_planning_provider_unavailable_does_not_bypass_relation(agent_factory):
    agent = agent_factory()
    request = relational()
    request.planning_mode = "llm"
    result = await agent.execute(request, "unit")
    assert (
        result.status == "failed"
        and result.error_code == "LLM_PLANNING_DISABLED"
        and not result.results
    )
    request.allow_fallback = True
    result = await agent.execute(request, "fallback")
    assert result.results and result.planner_mode == "deterministic_fallback"


async def test_request_state_isolation_and_invalid_evidence_rejection(agent_factory):
    agent = agent_factory(knowledge=FixtureKnowledge(valid=False))
    result = await agent.execute(relational(), "unit")
    assert (
        result.results == []
        and not result.query_success
        and result.error_code == "INVALID_KNOWLEDGE_EVIDENCE"
    )
    a = AgentState(AgentRequest(query="A"), "a", 999999, 6, 3)
    b = AgentState(AgentRequest(query="B"), "b", 999999, 6, 3)
    a.warnings.append("fixture")
    assert not b.warnings and a.query_id != b.query_id
    a.transition("running")
    a.transition("completed")
    with pytest.raises(AgentError):
        a.transition("running")


async def test_overall_deadline_during_rag_preserves_validated_images(agent_factory):
    class SlowRag(FixtureTools):
        async def invoke(self, name, args, state, emit):
            if name == "rag_explain":
                await asyncio.sleep(2)
            return await super().invoke(name, args, state, emit)

    agent = agent_factory(tools=SlowRag(), agent_timeout_seconds=0.03)
    result = await agent.execute(AgentRequest(query="a cup", include_explanation=True), "deadline")
    assert result.status == "partial" and len(result.results) == 1
    assert result.error_code == "AGENT_DEADLINE_EXCEEDED" and agent.inflight == 0


async def test_fabricated_image_ids_are_excluded(agent_factory):
    class Fabricated(FixtureTools):
        async def invoke(self, name, args, state, emit):
            identity = uuid4()
            return ToolOutput(image_ids=[identity], images=[image(identity)])

    result = await agent_factory(tools=Fabricated()).execute(AgentRequest(query="a cup"), "fake")
    assert result.results == [] and not result.query_success
    assert "STALE_IMAGES_EXCLUDED" in result.warnings


@pytest.mark.parametrize(
    "payload",
    [
        {"fixture": True},
        {
            "entities": [
                {
                    "id": str(IMAGE),
                    "canonical_name": "fixture",
                    "entity_type": "other",
                    "provenance": {"source_ref": "fixture://without-marker"},
                }
            ]
        },
    ],
)
async def test_fixture_import_rejects_serving_database(settings, payload):
    services = SimpleNamespace(
        settings=settings.model_copy(
            update={
                "app_env": "test",
                "agent_allow_fixture_knowledge": True,
            }
        )
    )
    with pytest.raises(ValueError, match="ISOLATED_AGENT_TEST_DATABASE"):
        await import_knowledge(services, payload)


async def test_invalid_llm_plans_stop_at_replanning_limit(agent_factory):
    class InvalidPlanner:
        def __init__(self):
            self.calls = 0

        async def generate(self, request, route, state, registry):
            self.calls += 1
            return AgentPlan(
                original_query=request.query,
                steps=[AgentPlanStep(step_id="bad", tool_name="shell", arguments={})],
            )

    agent = agent_factory(agent_max_replans=1)
    agent.planner = InvalidPlanner()
    request = relational()
    request.planning_mode = "llm"
    result = await agent.execute(request, "bad-plan")
    assert result.status == "failed" and result.tool_calls == 0
    assert agent.planner.calls == 2 and not result.plan_validated
    assert [t.error_code for t in result.planner_trace] == ["UNKNOWN_TOOL", "UNKNOWN_TOOL"]
    assert all(t.status == "failed" and t.duration_ms >= 0 for t in result.planner_trace)


async def test_planning_timeout_is_traced_even_when_replan_recovers(agent_factory):
    class RecoveringPlanner:
        calls = 0

        async def generate(self, request, route, state, registry):
            self.calls += 1
            state.planner_input_bytes = 500
            if self.calls == 1:
                raise AgentError("PLANNER_TIMEOUT", "timeout")
            return deterministic_plan(request, route)

    agent = agent_factory()
    agent.planner = RecoveringPlanner()
    request = relational()
    request.planning_mode = "llm"
    result = await agent.execute(request, "recover")
    assert result.plan_validated and result.results
    assert [t.status for t in result.planner_trace] == ["timeout", "completed"]
    assert result.planner_trace[0].error_code == "PLANNER_TIMEOUT"
    assert result.planner_trace[1].input_bytes == 500


async def test_permanent_planning_error_is_not_retried(agent_factory):
    agent = agent_factory()
    request = relational()
    request.planning_mode = "llm"
    result = await agent.execute(request, "disabled")
    assert len(result.planner_trace) == 1 and result.tool_calls == 0
    assert result.planner_trace[0].error_code == "LLM_PLANNING_DISABLED"


@pytest.mark.parametrize("code", ["LLM_AUTH_FAILED", "LLM_RATE_LIMITED"])
async def test_permanent_provider_error_does_not_replan(agent_factory, code):
    class Unavailable:
        calls = 0

        async def generate(self, *args):
            self.calls += 1
            raise AgentError(code)

    agent = agent_factory()
    agent.planner = Unavailable()
    request = relational()
    request.planning_mode = "llm"
    result = await agent.execute(request, "permanent")
    assert agent.planner.calls == 1 and result.error_code == code
    assert result.planner_trace[0].error_code == code and not result.results


async def test_concurrent_admission_is_bounded_and_request_states_are_separate(agent_factory):
    gate, ready = asyncio.Event(), asyncio.Event()

    class BlockingTools(FixtureTools):
        started = 0

        async def invoke(self, *args):
            self.started += 1
            if self.started == 2:
                ready.set()
            await gate.wait()
            return await super().invoke(*args)

    agent = agent_factory(tools=BlockingTools(), agent_max_concurrency=2)
    a = asyncio.create_task(agent.execute(AgentRequest(query="one"), "first"))
    b = asyncio.create_task(agent.execute(AgentRequest(query="two"), "second"))
    await asyncio.wait_for(ready.wait(), 1)
    try:
        with pytest.raises(AgentError, match="AGENT_BUSY"):
            await agent.execute(AgentRequest(query="three"), "third")
    finally:
        gate.set()
    first, second = await asyncio.gather(a, b)
    assert first.query_id != second.query_id and first.request_id == "first"
    assert second.request_id == "second" and first.tool_calls == second.tool_calls == 1
    assert agent.inflight == 0


def test_explicit_modes_precede_automatic_relational_detection():
    query = relational().query
    assert route_query(AgentRequest(query=query, mode="text")).strategy == "semantic"
    assert route_query(AgentRequest(query=query, mode="metadata")).strategy == "metadata"
    assert (
        route_query(AgentRequest(query=query, mode="explain", image_ids=[IMAGE])).strategy
        == "rag_explanation"
    )


async def test_generation_is_always_augmented_and_requested_mode_is_retained(agent_factory):
    result = await agent_factory().execute(
        AgentRequest(query="a cup", mode="text", include_explanation=True), "augmented"
    )
    assert result.service_class == "augmented" and result.requested_mode == "text"
