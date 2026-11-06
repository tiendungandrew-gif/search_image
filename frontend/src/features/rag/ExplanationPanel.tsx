import { useEffect, useRef, useState } from "react";
import type { SearchResponse } from "../../types/api";

type Answer = {
  answer: string;
  grounding_status: string;
  generated: boolean;
  error_code: string | null;
  citations: { image_id: string; evidence_field: string; quote: string }[];
};

export function ExplanationPanel({
  results,
  token,
  query,
}: {
  results: SearchResponse;
  token: string;
  query: string;
}) {
  const [question, setQuestion] = useState(
    query || "Tóm tắt bằng chứng hiện có.",
  );
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function explain() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError(null);
    setAnswer(null);
    const timer = setTimeout(() => request.abort(), 10000);
    try {
      const base = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
      const response = await fetch(`${base.replace(/\/$/, "")}/rag/explain`, {
        method: "POST",
        signal: request.signal,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question,
          language: "vi",
          image_ids: results.results.map((r) => r.image_id),
          expected_index_id: results.index_id,
        }),
      });
      const value = await response.json();
      if (!response.ok)
        throw new Error(value?.error?.message ?? "Không tạo được giải thích.");
      const rag = value.rag;
      const ids = new Set(results.results.map((r) => r.image_id));
      if (
        !rag ||
        typeof rag.answer !== "string" ||
        !Array.isArray(rag.citations) ||
        !rag.citations.every(
          (c: { image_id: string; quote: string }) =>
            ids.has(c.image_id) && typeof c.quote === "string",
        )
      )
        throw new Error("Phản hồi giải thích không đúng định dạng.");
      if (!request.signal.aborted) setAnswer(rag);
    } catch (err) {
      if (controller.current === request)
        setError(
          request.signal.aborted
            ? "Đã dừng yêu cầu giải thích."
            : err instanceof Error
              ? err.message
              : "Giải thích không khả dụng.",
        );
    } finally {
      clearTimeout(timer);
      if (controller.current === request) setLoading(false);
    }
  }
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
        {loading ? "Đang tạo giải thích…" : "Giải thích bằng AI"}
      </button>
      {loading && (
        <button
          className="text-button"
          type="button"
          onClick={() => controller.current?.abort()}
        >
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
