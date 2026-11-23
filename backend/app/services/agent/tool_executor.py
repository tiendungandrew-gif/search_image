import asyncio
from time import perf_counter

from app.core.exceptions import AppError
from app.evaluation.tracking import digest
from app.schemas.agent import StateReference, StepTrace, ToolOutput
from app.services.agent.errors import AgentError


class ToolExecutor:
    def __init__(self, tools, settings):
        self.tools, self.settings = tools, settings

    async def execute(self, step, definition, args, state, hop, emit):
        resolved = args.model_copy(deep=True)
        for key, value in args.__dict__.items():
            if isinstance(value, StateReference):
                previous = state.outputs.get(value.step_id)
                if previous is None or previous.insufficient:
                    raise AgentError("DEPENDENCY_UNRESOLVED", "insufficient_evidence")
                ids = getattr(previous, value.field)
                if not ids:
                    raise AgentError("MISSING_STATE_REFERENCE", "insufficient_evidence")
                setattr(resolved, key, list(ids))
        fingerprint_args = resolved.model_dump(mode="json")
        for field in ("image_ids", "entity_ids"):
            if isinstance(fingerprint_args.get(field), list):
                fingerprint_args[field] = sorted(set(fingerprint_args[field]))
        fingerprint = digest({"tool": definition.name, "args": fingerprint_args})
        if fingerprint in state.fingerprints:
            raise AgentError("LOOP_DETECTED")
        if state.tool_calls >= state.max_calls:
            raise AgentError("TOOL_CALL_LIMIT_EXCEEDED")
        state.fingerprints.add(fingerprint)
        state.tool_calls += 1
        state.logical_hops = max(state.logical_hops, hop)
        started = perf_counter()
        trace = StepTrace(
            step_id=step.step_id,
            tool=definition.name,
            status="running",
            duration_ms=0,
            logical_hop=hop,
        )
        state.traces.append(trace)
        try:
            await emit(
                "tool_started",
                {"step_id": step.step_id, "tool": definition.name, "logical_hop": hop},
            )
            timeout = (
                self.settings.rag_request_timeout_seconds
                if definition.capability == "rag"
                else self.settings.agent_tool_timeout_seconds
            )
            async with asyncio.timeout(min(timeout, state.remaining())):
                output = ToolOutput.model_validate(
                    await self.tools.invoke(definition.name, resolved, state, emit)
                )
            if len(output.model_dump_json().encode()) > 256 * 1024:
                raise AgentError("TOOL_OUTPUT_LIMIT")
            trace.status = "insufficient_evidence" if output.insufficient else "completed"
            trace.result_count = len(output.images) or len(output.entities)
            trace.evidence_ids = [str(r.evidence_id) for r in output.relations]
            state.outputs[step.step_id] = output
            state.warnings.extend(output.warnings)
            if output.insufficient:
                raise AgentError(
                    output.warnings[0] if output.warnings else "INSUFFICIENT_EVIDENCE",
                    "insufficient_evidence",
                )
            return output
        except asyncio.CancelledError:
            trace.status = "cancelled"
            raise
        except (TimeoutError, AppError) as error:
            trace.status = "timeout" if isinstance(error, TimeoutError) else "failed"
            trace.error_code = (
                "AGENT_DEADLINE_EXCEEDED"
                if isinstance(error, TimeoutError) and perf_counter() >= state.deadline
                else "TOOL_TIMEOUT"
                if isinstance(error, TimeoutError)
                else error.code
            )
            raise AgentError(
                trace.error_code, "timeout" if trace.status == "timeout" else "failed"
            ) from None
        except AgentError as error:
            trace.status = error.status
            trace.error_code = error.code
            raise
        except Exception:
            trace.status = "failed"
            trace.error_code = "TOOL_EXECUTION_FAILED"
            raise AgentError(trace.error_code) from None
        finally:
            trace.duration_ms = (perf_counter() - started) * 1000
            await emit("tool_completed", trace.model_dump(mode="json"))
