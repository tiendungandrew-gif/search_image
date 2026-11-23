import { useCallback, useEffect, useRef, useState } from "react";
import { api, APIClientError } from "../../services/api/client";
import type { AdvancedSearchInput, SearchResponse } from "../../types/api";
import { searchAgent, type AgentResponse } from "../agent/api";
import { toolLabels } from "../agent/tools";

export type SearchState =
  | "IDLE"
  | "VALIDATING"
  | "SEARCHING"
  | "SUCCESS"
  | "EMPTY"
  | "INDEX_NOT_READY"
  | "ERROR"
  | "CANCELLED";
export function useSearchSession(token: string) {
  const lastSearch = useRef<{
    input: AdvancedSearchInput;
    image: File | null;
    agentOptions: { includeExplanation: boolean; planner: string };
  } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const [sessionToken, setSessionToken] = useState(token);
  const [state, setState] = useState<SearchState>("IDLE");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [agent, setAgent] = useState<AgentResponse | null>(null);
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [metrics, setMetrics] = useState<{
    started: number;
    apiMs: number | null;
    visibleMs: number | null;
    renderMs: number | null;
    reactMs: number | null;
  }>({
    started: 0,
    apiMs: null,
    visibleMs: null,
    renderMs: null,
    reactMs: null,
  });
  const reset = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
    setSessionToken(token);
    lastSearch.current = null;
    setState("IDLE");
    setResults(null);
    setAgent(null);
    setError(null);
    setProgress([]);
  }, [token]);
  useEffect(
    () => () => {
      controller.current?.abort();
      controller.current = null;
    },
    [token],
  );
  function cancel() {
    controller.current?.abort();
    controller.current = null;
    setState("CANCELLED");
    setError(null);
  }
  function validationError(message: string) {
    setSessionToken(token);
    setState("VALIDATING");
    setError(new Error(message));
  }
  async function execute(
    input: AdvancedSearchInput,
    image: File | null,
    agentOptions: { includeExplanation: boolean; planner: string },
  ) {
    lastSearch.current = { input, image, agentOptions };
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    const current = () =>
      controller.current === request && !request.signal.aborted;
    const started = performance.now();
    setSessionToken(token);
    setState("SEARCHING");
    setError(null);
    setResults(null);
    setAgent(null);
    setProgress([]);
    setSubmittedQuery(input.text ?? "");
    setMetrics({
      started,
      apiMs: null,
      visibleMs: null,
      renderMs: null,
      reactMs: null,
    });
    try {
      if (input.mode === "agent") {
        const response = await searchAgent(
          {
            query: input.text,
            mode: "agent",
            top_k: input.top_k,
            include_explanation: agentOptions.includeExplanation,
            planning_mode: agentOptions.planner,
            rerank: input.rerank?.enabled ?? false,
          },
          token,
          request.signal,
          (event, data) => {
            if (!current()) return;
            const label =
              event === "planning_started"
                ? "Đang lập kế hoạch"
                : event === "planning_completed"
                  ? "Đã kiểm tra kế hoạch"
                  : event === "tool_started"
                    ? `${toolLabels[String(data.tool)] ?? "Đang truy xuất"}…`
                    : event === "tool_completed"
                      ? "Đã hoàn tất công cụ"
                      : event === "retrieval_completed"
                        ? "Đã truy xuất ảnh"
                        : event === "generation_started"
                          ? "Đang tạo giải thích"
                          : null;
            if (label) setProgress((old) => [...old.slice(-29), label]);
          },
        );
        if (!current()) return;
        setAgent(response);
        setState(response.results.length ? "SUCCESS" : "EMPTY");
      } else {
        const response = await api.searchAdvanced(
          { ...input, page: input.page ?? 1 },
          image,
          token,
          request.signal,
        );
        if (!current()) return;
        setResults(response);
        setState(response.results.length ? "SUCCESS" : "EMPTY");
      }
      setMetrics({
        started,
        apiMs: performance.now() - started,
        visibleMs: null,
        renderMs: null,
        reactMs: null,
      });
    } catch (issue) {
      if (!current()) return;
      setError(
        issue instanceof Error ? issue : new Error("Không tìm kiếm được."),
      );
      setState(
        issue instanceof APIClientError &&
          ["NOT_READY", "INDEX_NOT_READY"].includes(issue.code)
          ? "INDEX_NOT_READY"
          : "ERROR",
      );
    }
  }
  const markVisible = useCallback(
    () =>
      setMetrics((old) =>
        old.visibleMs !== null || !old.apiMs
          ? old
          : {
              ...old,
              visibleMs: performance.now() - old.started,
              renderMs: performance.now() - old.started - old.apiMs,
            },
      ),
    [],
  );
  const markReact = useCallback(
    (_id: string, _phase: string, duration: number) =>
      setMetrics((old) =>
        old.reactMs !== null ? old : { ...old, reactMs: duration },
      ),
    [],
  );
  const current = sessionToken === token;
  return {
    state: current ? state : "IDLE",
    results: current ? results : null,
    agent: current ? agent : null,
    progress: current ? progress : [],
    error: current ? error : null,
    submittedQuery,
    metrics: current
      ? metrics
      : {
          started: 0,
          apiMs: null,
          visibleMs: null,
          renderMs: null,
          reactMs: null,
        },
    execute,
    goToPage: (page: number) => {
      const previous = lastSearch.current;
      if (
        !current ||
        !previous ||
        state === "SEARCHING" ||
        !results?.pagination ||
        page < 1 ||
        page > results.pagination.total_pages
      )
        return;
      return execute(
        { ...previous.input, page },
        previous.image,
        previous.agentOptions,
      );
    },
    reset,
    cancel,
    validationError,
    markVisible,
    markReact,
  };
}
