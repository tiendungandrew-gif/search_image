import asyncio
from time import perf_counter

from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.agent import AgentPlanStep, PlanningAttemptTrace
from app.services.agent.errors import AgentError
from app.services.agent.evidence_aggregator import EvidenceAggregator
from app.services.agent.multi_hop import execute_plan
from app.services.agent.plan_validator import validate_plan
from app.services.agent.planner import Planner, deterministic_plan
from app.services.agent.response_builder import build_response
from app.services.agent.router import route_query
from app.services.agent.state import AgentState
from app.services.agent.tool_executor import ToolExecutor
from app.services.agent.tool_registry import build_registry
from app.services.agent.tools import AgentTools
from app.services.rag.rag_service import silent_emit


class AgentService:
    def __init__(self, services, runtime, generator, *, knowledge=None, tools=None):
        self.settings = services.settings
        self.services, self.runtime, self.generator = services, runtime, generator
        self.knowledge = knowledge or KnowledgeRepository(services)
        self.registry = build_registry()
        self.planner = Planner(self.settings)
        self.tools = tools or AgentTools(services, runtime, generator, self.knowledge)
        self.executor = ToolExecutor(self.tools, self.settings)
        self.aggregator = EvidenceAggregator(runtime, self.knowledge)
        self.inflight = 0

    async def close(self):
        await self.planner.close()

    async def execute(self, request, request_id, emit=silent_emit):
        cfg = self.settings
        if self.inflight >= cfg.agent_max_concurrency:
            raise AgentError("AGENT_BUSY")
        self.inflight += 1
        started = perf_counter()
        deadline = min(cfg.agent_timeout_seconds, request.budgets.deadline_ms / 1000)
        state = AgentState(
            request,
            request_id,
            started + deadline,
            min(cfg.agent_max_tool_calls, request.budgets.max_tool_calls),
            min(cfg.agent_max_hops, request.budgets.max_hops),
        )
        mark = perf_counter()
        route = route_query(request, cfg.agent_router_enabled)
        state.require_entity_links = bool(route.anchor)
        state.started_at = started
        if route.uncertain:
            state.warnings.append("QUERY_INTERPRETATION_LIMITED")
        timings = {
            "routing_ms": (perf_counter() - mark) * 1000,
            "planning_ms": 0.0,
            "aggregation_ms": 0.0,
            "provider_ttft_ms": None,
            "provider_ttlast_ms": None,
            "request_ttlast_ms": None,
        }
        planner_mode = request.planning_mode or cfg.agent_planner_mode
        if route.strategy != "agentic_multi_hop":
            planner_mode = "deterministic"
        dataset = "unknown"
        error_code = None
        planning_started = None
        empty = ([], [], [], [], None, {})
        aggregated = empty
        try:
            state.transition("running")
            async with asyncio.timeout(deadline):
                await emit(
                    "planning_started", {"strategy": route.strategy, "planner_mode": planner_mode}
                )
                if route.strategy == "unsupported_relation":
                    raise AgentError("UNSUPPORTED_RELATIONAL_PATTERN", "insufficient_evidence")
                mark = perf_counter()
                planning_started = mark
                if planner_mode == "llm":
                    last_error = None
                    validated = None
                    permanent_errors = {
                        "LLM_PLANNING_DISABLED",
                        "LLM_AUTH_FAILED",
                        "LLM_ACCESS_DENIED",
                        "LLM_MODEL_UNAVAILABLE",
                        "LLM_RATE_LIMITED",
                        "RAG_INVALID_CONFIG",
                        "RAG_KEY_MISSING",
                        "PLAN_INPUT_LIMIT",
                    }
                    for number in range(cfg.agent_max_replans + 1):
                        attempt_started = perf_counter()
                        trace = PlanningAttemptTrace(attempt=number + 1, status="running")
                        state.planner_trace.append(trace)
                        state.planner_input_bytes = 0
                        try:
                            state.plan = await self.planner.generate(
                                request, route, state, self.registry
                            )
                            validated = validate_plan(
                                state.plan,
                                request,
                                route,
                                self.registry,
                                state.max_calls,
                                state.max_hops,
                            )
                            trace.status = "completed"
                            break
                        except AgentError as error:
                            last_error = error
                            trace.status = "timeout" if error.status == "timeout" else "failed"
                            trace.error_code = error.code
                            if error.code in permanent_errors:
                                break
                        except asyncio.CancelledError:
                            expired = perf_counter() >= state.deadline
                            trace.status = "timeout" if expired else "cancelled"
                            trace.error_code = (
                                "AGENT_DEADLINE_EXCEEDED" if expired else "REQUEST_CANCELLED"
                            )
                            raise
                        except Exception:
                            trace.status = "failed"
                            trace.error_code = "PLANNER_EXECUTION_FAILED"
                            raise AgentError("PLANNER_EXECUTION_FAILED") from None
                        finally:
                            trace.duration_ms = (perf_counter() - attempt_started) * 1000
                            trace.input_bytes = state.planner_input_bytes
                    if validated is None:
                        if not (request.allow_fallback and cfg.agent_enable_fallback):
                            raise last_error
                        state.warnings.append("DETERMINISTIC_PLANNING_FALLBACK")
                        planner_mode = "deterministic_fallback"
                        state.plan = deterministic_plan(request, route)
                        validated = validate_plan(
                            state.plan,
                            request,
                            route,
                            self.registry,
                            state.max_calls,
                            state.max_hops,
                        )
                else:
                    state.plan = deterministic_plan(request, route)
                    validated = validate_plan(
                        state.plan, request, route, self.registry, state.max_calls, state.max_hops
                    )
                timings["planning_ms"] = (perf_counter() - mark) * 1000
                state.plan_validated = True
                await emit(
                    "planning_completed",
                    {
                        "plan_id": str(state.plan.plan_id),
                        "steps": len(state.plan.steps),
                        "max_hops": state.max_hops,
                    },
                )
                dataset = await self.knowledge.dataset_status(self.runtime)
                if dataset != "available":
                    raise AgentError(
                        "EMPTY_DATASET" if dataset == "empty_dataset" else "SEARCH_UNAVAILABLE",
                        "insufficient_evidence" if cfg.agent_allow_empty_dataset else "failed",
                    )
                await execute_plan(*validated, self.registry, self.executor, state, emit)
                mark = perf_counter()
                aggregated = await self.aggregator.aggregate(state)
                timings["aggregation_ms"] = (perf_counter() - mark) * 1000
                await emit(
                    "retrieval_completed",
                    {"image_count": len({i for o in state.outputs.values() for i in o.image_ids})},
                )
                if request.include_explanation:
                    ids = [image.image_id for image in aggregated[0]]
                    if ids:
                        try:
                            step = AgentPlanStep(
                                step_id="answer",
                                tool_name="rag_explain",
                                arguments={"image_ids": [str(i) for i in ids]},
                            )
                            args = self.registry[step.tool_name].input_model.model_validate(
                                step.arguments
                            )
                            await self.executor.execute(
                                step,
                                self.registry[step.tool_name],
                                args,
                                state,
                                state.logical_hops,
                                emit,
                            )
                        except AgentError as error:
                            if error.code == "AGENT_DEADLINE_EXCEEDED":
                                raise
                            state.warnings.append(error.code)
                if "answer" in state.outputs:
                    mark = perf_counter()
                    aggregated = await self.aggregator.aggregate(state)
                    timings["aggregation_ms"] += (perf_counter() - mark) * 1000
                images, _, _, _, rag, _ = aggregated
                for output in state.outputs.values():
                    if output.rag:
                        timings["provider_ttft_ms"] = output.timing.get("provider_ttft_ms")
                        timings["provider_ttlast_ms"] = output.timing.get("provider_ttlast_ms")
                        delta = output.timing.get("time_to_last_token_from_request_ms")
                        timings["request_ttlast_ms"] = (
                            output.timing["agent_rag_started_ms"] + delta
                            if delta is not None
                            else None
                        )
                state.transition(
                    "completed"
                    if images and not state.warnings and (not rag or not rag.error_code)
                    else "partial"
                    if images
                    else "insufficient_evidence"
                )
        except asyncio.CancelledError:
            state.transition("cancelled")
            raise
        except (AgentError, TimeoutError) as error:
            error_code = error.code if isinstance(error, AgentError) else "AGENT_DEADLINE_EXCEEDED"
            desired = error.status if isinstance(error, AgentError) else "timeout"
            state.warnings.append(error_code)
            # Keep only fully revalidated earlier results, within the original deadline.
            if state.outputs and perf_counter() < state.deadline:
                try:
                    async with asyncio.timeout(state.remaining()):
                        aggregated = await self.aggregator.aggregate(state)
                except Exception:
                    aggregated = empty
            state.transition("partial" if aggregated[0] else desired)
        except Exception:
            error_code = "AGENT_DEPENDENCY_FAILED"
            state.transition("failed")
        finally:
            if planning_started is not None and not state.plan_validated:
                timings["planning_ms"] = (perf_counter() - planning_started) * 1000
            self.inflight -= 1
            timings["total_ms"] = (perf_counter() - started) * 1000
            timings["tools_ms"] = sum(t.duration_ms for t in state.traces)
        return build_response(
            state, route, dataset, planner_mode, aggregated, timings, self.runtime, error_code
        )
