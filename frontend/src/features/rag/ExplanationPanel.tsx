import { useEffect, useRef, useState } from "react";
import type { SearchResponse, RagAnswer } from "../../types/api";
import { api } from "../../services/api/client";
import { decodeRag, record } from "../../services/api/decoders";
import { postStream } from "../../services/api/stream";

// Backend bounds the whole RAG request to at most 60 seconds.
const CLIENT_TIMEOUT_MS = 65_000;
const RETRYABLE_CODES = new Set([
  "LLM_TIMEOUT",
  "LLM_CONNECTION_FAILED",
  "LLM_RATE_LIMITED",
  "LLM_PROVIDER_ERROR",
  "LLM_INCOMPLETE_STREAM",
  "RAG_BUSY",
]);

export function ExplanationPanel({
  results,
  token,
  query,
  streaming = false,
}: {
  results: SearchResponse;
  token: string;
  query: string;
  streaming?: boolean;
}) {
  const [question, setQuestion] = useState(
    query || "Tóm tắt bằng chứng hiện có.",
  );
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [progress, setProgress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  function cancel() {
    const pending = controller.current;
    controller.current = null;
    pending?.abort();
    setLoading(false);
    setError("Đã dừng yêu cầu giải thích.");
  }
  useEffect(
    () => () => {
      const pending = controller.current;
      controller.current = null;
      pending?.abort();
    },
    [],
  );
  async function explain() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError(null);
    setAnswer(null);
    setProgress("");
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      request.abort();
    }, CLIENT_TIMEOUT_MS);
    try {
      const ids = results.results.map((r) => r.image_id);
      const body = {
        question,
        language: "vi",
        image_ids: ids,
        expected_index_id: results.index_id,
      };
      const rag = streaming
        ? await postStream(
            "/rag/explain/stream",
            body,
            token,
            request.signal,
            (event, value) => {
              if (event === "generation_completed")
                return decodeRag(value, new Set(ids));
              if (
                event === "error" &&
                record(value) &&
                value.retrieval_preserved === true
              )
                return undefined;
              if (event === "error")
                throw new Error(
                  `RAG dừng: ${record(value) && typeof value.code === "string" ? value.code : "RAG_FAILED"}`,
                );
              if (controller.current === request && !request.signal.aborted) {
                const messages: Record<string, string> = {
                  retrieval_started: "Đang kiểm tra các ảnh đã chọn…",
                  retrieval_completed: "Đã kiểm tra ảnh.",
                  context_built: "Đã chuẩn bị bằng chứng.",
                  generation_started: "Đang tạo câu trả lời…",
                };
                if (messages[event]) setProgress(messages[event]);
              }
              return undefined;
            },
          )
        : await api.explain(body, ids, token, request.signal);
      if (controller.current === request && !request.signal.aborted)
        setAnswer(rag);
    } catch (err) {
      if (controller.current === request)
        setError(
          request.signal.aborted
            ? timedOut
              ? "Yêu cầu giải thích quá thời gian chờ. Bạn có thể thử lại."
              : "Đã dừng yêu cầu giải thích."
            : err instanceof Error
              ? err.message
              : "Giải thích không khả dụng.",
        );
    } finally {
      clearTimeout(timer);
      if (controller.current === request) setLoading(false);
    }
  }
  const retryable = Boolean(
    error || (answer?.error_code && RETRYABLE_CODES.has(answer.error_code)),
  );
  return (
    <section
      className="explanation-panel"
      aria-labelledby="explanation-heading"
    >
      <h3 id="explanation-heading">Giải thích kết quả</h3>
      <p className="muted">
        Dùng thông tin đã lưu của các ảnh. Nội dung ảnh chỉ được xác nhận khi có
        bằng chứng phù hợp.
      </p>
      <label className="field-label" htmlFor="rag-question">
        Bạn muốn biết điều gì?
      </label>
      <textarea
        id="rag-question"
        maxLength={2000}
        rows={2}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button
        type="button"
        className="diagnostic-button"
        disabled={loading || !question.trim()}
        onClick={() => void explain()}
      >
        {loading
          ? "Đang tạo giải thích…"
          : retryable
            ? "Thử lại giải thích"
            : "Giải thích bằng AI"}
      </button>
      {loading && (
        <p role="status">{progress || "Đang kiểm tra bằng chứng…"}</p>
      )}
      {loading && (
        <button className="text-button" type="button" onClick={cancel}>
          Dừng giải thích
        </button>
      )}
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
      {answer && (
        <div role="status" data-testid="rag-answer">
          <p className="availability-note">
            {answer.grounding_status === "supported"
              ? "Có bằng chứng metadata"
              : answer.grounding_status === "partially_supported"
                ? "Bằng chứng còn giới hạn"
                : answer.grounding_status === "insufficient_evidence"
                  ? "Chưa đủ bằng chứng"
                  : "Giải thích chưa khả dụng"}
          </p>
          <p style={{ whiteSpace: "pre-wrap" }}>{answer.answer}</p>
          {answer.error_code && (
            <p className="muted">
              Mã trạng thái: {answer.error_code}. Bạn vẫn có thể xem và tìm kiếm
              ảnh.
            </p>
          )}
          <ul>
            {answer.citations.map((c, i) => (
              <li key={`${c.image_id}-${i}`}>
                <a href={`#image-${c.image_id}`}>
                  Ảnh {c.image_id.slice(0, 8)}
                </a>{" "}
                · {c.evidence_field}: {c.quote}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
