"""Validate the full DAG and typed references before executing any tool."""

from pydantic import ValidationError

from app.schemas.agent import StateReference
from app.services.agent.errors import AgentError
from app.services.agent.planner import deterministic_plan


def validate_plan(plan, request, route, registry, max_calls, max_hops, *, constrain_relations=True):
    if plan.original_query != request.query or len(plan.steps) > max_calls:
        raise AgentError("PLAN_BUDGET_OR_QUERY_MISMATCH")
    steps = {s.step_id: s for s in plan.steps}
    if len(steps) != len(plan.steps):
        raise AgentError("DUPLICATE_PLAN_STEP")
    normalized = {}
    for step in plan.steps:
        definition = registry.get(step.tool_name)
        if definition is None:
            raise AgentError("UNKNOWN_TOOL")
        if len(set(step.depends_on)) != len(step.depends_on) or any(
            i not in steps or i == step.step_id for i in step.depends_on
        ):
            raise AgentError("INVALID_DEPENDENCY")
        try:
            args = definition.input_model.model_validate(step.arguments)
        except ValidationError:
            raise AgentError("INVALID_TOOL_ARGUMENTS") from None
        for value in args.__dict__.values():
            if isinstance(value, StateReference):
                if value.step_id not in step.depends_on:
                    raise AgentError("UNDECLARED_STATE_REFERENCE")
                producer = steps[value.step_id].tool_name
                entity_producer = producer in {
                    "entity_lookup",
                    "relationship_lookup",
                    "get_related_entities",
                }
                if (value.field == "entity_ids") != entity_producer:
                    raise AgentError("INVALID_REFERENCE_TYPE")
        normalized[step.step_id] = args
    ordered = []
    hops = {}
    while len(ordered) < len(steps):
        ready = [
            s for s in plan.steps if s.step_id not in hops and all(d in hops for d in s.depends_on)
        ]
        if not ready:
            raise AgentError("CYCLIC_PLAN")
        for step in ready:
            hop = (
                max((hops[d] for d in step.depends_on), default=0)
                + registry[step.tool_name].hop_cost
            )
            if hop > min(max_hops, plan.max_hops):
                raise AgentError("HOP_LIMIT_EXCEEDED")
            hops[step.step_id] = hop
            ordered.append(step)
    if route.anchor and constrain_relations:
        required = deterministic_plan(request, route)
        expected = {s.step_id: s for s in required.steps}
        # An LLM cannot remove the relation gate, change the anchor, or weaken filters.
        if set(steps) != set(expected):
            raise AgentError("UNSUPPORTED_RELATIONAL_PLAN")
        for identity, step in steps.items():
            other = expected[identity]
            expected_args = registry[other.tool_name].input_model.model_validate(other.arguments)
            if (
                step.tool_name != other.tool_name
                or set(step.depends_on) != set(other.depends_on)
                or normalized[identity] != expected_args
            ):
                raise AgentError("UNSUPPORTED_RELATIONAL_PLAN")
    return ordered, normalized, hops
