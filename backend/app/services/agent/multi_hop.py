from app.services.agent.errors import AgentError


async def execute_plan(ordered, arguments, hops, registry, executor, state, emit):
    for step in ordered:
        state.remaining()
        if any(d not in state.outputs or state.outputs[d].insufficient for d in step.depends_on):
            raise AgentError("DEPENDENCY_UNRESOLVED", "insufficient_evidence")
        await executor.execute(
            step, registry[step.tool_name], arguments[step.step_id], state, hops[step.step_id], emit
        )
        # An outward located_in chain returning an already visited subject is a graph cycle.
        if step.tool_name == "relationship_lookup":
            edges = [
                r
                for value in state.outputs.values()
                for r in value.relations
                if r.predicate == "located_in"
            ]
            graph = {r.subject_id: r.object_id for r in edges}
            for start in graph:
                seen = set()
                current = start
                while current in graph:
                    if current in seen:
                        raise AgentError("CYCLIC_ENTITY_LOOKUP")
                    seen.add(current)
                    current = graph[current]
