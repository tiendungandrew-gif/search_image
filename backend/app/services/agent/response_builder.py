from app.schemas.agent import AgentResponse


def build_response(
    state, route, dataset, planner_mode, aggregated, timings, runtime, error_code=None
):
    images, entities, relations, associations, rag, sources = aggregated
    names = {e.entity_id: e.canonical_name for e in entities}
    summaries = []
    for relation in relations:
        if relation.subject_id in names and relation.object_id in names:
            summaries.append(
                f"{names[relation.subject_id]} — {relation.predicate} → {names[relation.object_id]}"
            )
    relationship_summary = "; ".join(summaries) or None
    registry = runtime.registry if runtime and runtime.available else None
    return AgentResponse(
        query_id=state.query_id,
        request_id=state.request_id,
        execution_id=state.execution_id,
        index_id=registry.index.id if registry else None,
        model_id=registry.model.id if registry else None,
        manifest_sha256=registry.model.manifest_sha256 if registry else None,
        requested_mode=state.request.mode,
        search_mode="agent"
        if route.anchor or route.strategy == "unsupported_relation"
        else "text"
        if route.strategy == "semantic"
        else route.strategy,
        service_class="fast"
        if route.strategy == "semantic" and not state.request.include_explanation
        else "augmented",
        status=state.status,
        query_success=state.status == "completed" and bool(images),
        dataset_status=dataset,
        results=images,
        resolved_entities=entities,
        steps=state.traces,
        evidence=relations,
        image_associations=associations,
        image_sources=sources,
        answer=rag.answer if rag else None,
        rag=rag,
        relationship_summary=relationship_summary,
        planner_mode=planner_mode,
        planner_attempts=state.planner_attempts,
        planner_trace=state.planner_trace,
        plan_validated=state.plan_validated,
        planner_usage=state.planner_usage,
        planner_model_id=state.planner_model_id,
        planner_prompt_sha256=state.planner_prompt_sha256,
        plan_id=state.plan.plan_id if state.plan else None,
        logical_hops=state.logical_hops,
        tool_calls=state.tool_calls,
        latency_ms=timings["total_ms"],
        latency=timings,
        warnings=list(dict.fromkeys(state.warnings)),
        error_code=error_code,
        verification_state="TESTED_WITH_MOCKS"
        if any(e.fixture for e in entities)
        else "VERIFIED_WITH_REAL_DATA"
        if images
        else "NOT_VERIFIED",
    )
