import { ResultGallery } from "../search/ResultGallery";
import { useEffect } from "react";
import type { AgentResponse } from "./api";

import { toolLabels } from "./tools";

function publicSource(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}
export function AgentResults({
  response,
  progress,
  loading,
  token,
  showDiagnostics = true,
  datasetNames,
}: {
  response: AgentResponse | null;
  progress: string[];
  loading: boolean;
  token: string;
  showDiagnostics?: boolean;
  datasetNames?: Record<string, string>;
}) {
  useEffect(() => {
    if (!response?.results.length) return;
    const frame = requestAnimationFrame(() =>
      document.getElementById(`image-${response.results[0].image_id}`)?.focus(),
    );
    return () => cancelAnimationFrame(frame);
  }, [response]);
  return (
    <section
      className="results-section"
      aria-labelledby="agent-results-heading"
      data-testid="agent-results"
    >
      <h2 id="agent-results-heading">
        {showDiagnostics ? "Kết quả Agent Search" : "Kết quả theo mối liên hệ"}
      </h2>
      {loading && <p role="status">Đang xử lý truy vấn…</p>}
      <ol
        className="agent-progress"
        aria-label="Tiến độ Agent"
        aria-live="polite"
      >
        {progress.map((message, i) => (
          <li key={i}>{message}</li>
        ))}
      </ol>
      {response && (
        <>
          <p className="availability-note" data-testid="agent-status">
            {response.status === "completed"
              ? "Đã hoàn tất truy xuất"
              : response.status === "partial"
                ? "Kết quả một phần"
                : response.status === "timeout"
                  ? "Đã hết thời gian xử lý"
                  : response.status === "failed"
                    ? "Chưa thể hoàn thành yêu cầu"
                    : "Chưa đủ bằng chứng để trả lời"}
            {showDiagnostics && ` · ${response.latency_ms.toFixed(1)} ms`}
          </p>
          {response.dataset_status === "empty_dataset" && (
            <p>
              Chưa có dữ liệu ảnh để tìm kiếm. Bạn vẫn có thể sử dụng các chức
              năng khác.
            </p>
          )}
          {!response.results.length &&
            response.status === "insufficient_evidence" &&
            response.dataset_status !== "empty_dataset" && (
              <p>
                Chưa tìm được ảnh có đủ bằng chứng cho truy vấn này. Quan hệ
                chưa được xác nhận sẽ không được dùng để suy đoán kết quả.
              </p>
            )}
          {response.warnings.includes("LLM_RATE_LIMITED") && (
            <p role="status">
              Dịch vụ AI đang giới hạn tần suất. Bạn có thể thử lại sau hoặc
              chọn “Theo mẫu đã hỗ trợ” ở mục Lập kế hoạch. Các ảnh đã tìm được
              vẫn được giữ lại.
            </p>
          )}
          {showDiagnostics && response.steps.length > 0 && (
            <ol aria-label="Các bước đã thực hiện">
              {response.steps.map((step) => (
                <li key={step.step_id}>
                  {toolLabels[step.tool] ?? step.tool} · {step.status} ·{" "}
                  {step.duration_ms.toFixed(1)} ms
                </li>
              ))}
            </ol>
          )}
          {response.relationship_summary && (
            <p>
              Quan hệ có nguồn trong dữ liệu: {response.relationship_summary}
            </p>
          )}
          {response.evidence?.some((e) => e.verified) && (
            <details>
              <summary>Nguồn quan hệ</summary>
              <ul>
                {[
                  ...new Set(
                    response.evidence
                      .filter((e) => e.verified)
                      .map((e) => e.source_ref),
                  ),
                ].map((source) => {
                  const href = publicSource(source);
                  return (
                    <li key={source}>
                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {source}
                        </a>
                      ) : (
                        <span>{source}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          )}
          {response.rag && (
            <div className="explanation-panel">
              <h3>Giải thích</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>{response.rag.answer}</p>
              <ul>
                {response.rag.citations.map((c, i) => (
                  <li key={i}>
                    <a href={`#image-${c.image_id}`}>
                      Ảnh {c.image_id.slice(0, 8)}
                    </a>{" "}
                    · {c.quote}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {response.resolved_entities &&
            response.resolved_entities.length > 0 && (
              <ul className="entity-list" aria-label="Thực thể đã xác định">
                {response.resolved_entities.map((entity) => (
                  <li key={entity.entity_id}>
                    {entity.canonical_name} · {entity.entity_type}
                  </li>
                ))}
              </ul>
            )}
          {response.results.length > 0 && (
            <ResultGallery
              key={response.query_id}
              images={response.results}
              token={token}
              showDiagnostics={showDiagnostics}
              datasetNames={datasetNames}
            />
          )}
          {showDiagnostics && response.error_code && (
            <p className="availability-note">
              Trạng thái: {response.error_code}
            </p>
          )}
        </>
      )}
    </section>
  );
}
