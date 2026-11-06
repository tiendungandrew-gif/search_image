import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";

import { api } from "../../services/api/client";
import type {
  SearchMode,
  SearchResponse,
  AdvancedSearchInput,
} from "../../types/api";
import { ResultImage } from "./ResultImage";
import { ExplanationPanel } from "../rag/ExplanationPanel";

export function SearchWorkspace({
  token,
  onTokenChange,
  available = false,
}: {
  token: string;
  onTokenChange: (value: string) => void;
  available?: boolean;
}) {
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(10);
  const [resultToken, setResultToken] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await api.searchAdvanced(
        {
          mode,
          ...(mode !== "image" && query.trim() ? { text: query } : {}),
          top_k: topK,
          rerank: { enabled: rerank, on_failure: "skip" },
          ...(mode === "multimodal" || (mode === "auto" && file)
            ? {
                fusion: {
                  method: fusion,
                  text_weight: textWeight,
                  image_weight: 1 - textWeight,
                },
              }
            : {}),
        },
        mode === "image" || mode === "multimodal" || mode === "auto"
          ? file
          : null,
        token,
        request.signal,
      );
      if (!request.signal.aborted) {
        setResults(response);
        setResultToken(token);
      }
    } catch (err) {
      if (!request.signal.aborted)
        setError(err instanceof Error ? err.message : "Không tìm kiếm được");
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("auto");
  const [fusion, setFusion] =
    useState<NonNullable<AdvancedSearchInput["fusion"]>["method"]>("rrf");
  const [textWeight, setTextWeight] = useState(0.5);
  const [rerank, setRerank] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);
  function chooseFile(selected?: File) {
    setError(null);
    setFile(null);
    setPreview(null);
    if (!selected) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(selected.type)) {
      setError("Chọn ảnh JPEG, PNG hoặc WebP.");
      return;
    }
    if (selected.size > 20 * 1024 * 1024) {
      setError("Ảnh vượt giới hạn xem trước 20 MiB.");
      return;
    }
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  }
  return (
    <>
      <section className="search-card" aria-labelledby="search-heading">
        <div className="card-kicker">
          <span className="accent-dot" /> KHÔNG GIAN TÌM KIẾM{" "}
          <span className="soon-badge">
            {available ? "Semantic Search" : "Đang chờ chỉ mục"}
          </span>
        </div>
        <h2 id="search-heading">Bắt đầu bằng một ý tưởng.</h2>
        <p className="muted">
          Mô tả điều bạn đang tìm hoặc chọn một ảnh làm điểm xuất phát.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <label className="field-label" htmlFor="search-token">
            Token truy cập
          </label>
          <input
            id="search-token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => {
              controller.current?.abort();
              setLoading(false);
              setResults(null);
              onTokenChange(e.target.value);
            }}
          />
          <p className="muted">Token chỉ giữ trong phiên này.</p>
          <label className="field-label" htmlFor="query">
            Bạn đang tìm hình ảnh nào?
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={2000}
            placeholder="Ví dụ: Một chiếc xe máy màu đỏ trên con phố sau cơn mưa…"
            rows={3}
          />
          <div className="form-row">
            <div className="mode-field">
              <label htmlFor="mode">Phương thức</label>
              <select
                id="mode"
                value={mode}
                onChange={(e) => setMode(e.target.value as SearchMode)}
              >
                <option value="auto">Tự động theo đầu vào</option>
                <option value="text">Văn bản → Hình ảnh</option>
                <option value="image">Hình ảnh → Hình ảnh</option>
                <option value="multimodal">Văn bản + Hình ảnh</option>
                <option value="multi_intent">Nhiều điều kiện · AND / OR</option>
              </select>
            </div>
            <button
              className="search-button"
              type="submit"
              disabled={
                !available ||
                !token ||
                loading ||
                (mode === "multimodal"
                  ? !file || !query.trim()
                  : mode === "image"
                    ? !file
                    : mode === "auto"
                      ? !file && !query.trim()
                      : !query.trim())
              }
              aria-describedby="search-unavailable"
            >
              <Icon kind="search" />
              {loading ? "Đang tìm kiếm…" : "Tìm kiếm ảnh"}
              <Icon kind="arrow" />
            </button>
          </div>
          <label className="field-label" htmlFor="top-k">
            Số kết quả
          </label>
          <input
            id="top-k"
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) =>
              setTopK(Math.max(1, Math.min(50, Number(e.target.value) || 1)))
            }
          />
          <details className="advanced-controls">
            <summary>Tùy chọn tìm kiếm nâng cao</summary>
            <label className="field-label" htmlFor="fusion-strategy">
              Kết hợp kết quả
            </label>
            <select
              id="fusion-strategy"
              value={fusion}
              onChange={(e) => setFusion(e.target.value as typeof fusion)}
            >
              <option value="rrf">RRF · theo thứ hạng</option>
              <option value="weighted_score">
                Weighted score · cosine đã đổi thang
              </option>
            </select>
            <label className="field-label" htmlFor="text-weight">
              Trọng số văn bản {textWeight.toFixed(2)} · ảnh{" "}
              {(1 - textWeight).toFixed(2)}
            </label>
            <input
              id="text-weight"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={textWeight}
              onChange={(e) => setTextWeight(Number(e.target.value))}
            />
            <label className="rerank-control">
              <input
                type="checkbox"
                checked={rerank}
                onChange={(e) => setRerank(e.target.checked)}
              />{" "}
              Xếp hạng lại theo điều kiện
            </label>
            <p className="muted">
              Áp dụng trọng số khi có cả văn bản và ảnh. Điều kiện thị giác có
              thể chưa xác minh.
            </p>
          </details>
          <label
            className={`upload-area ${preview ? "has-preview" : ""}`}
            htmlFor="reference-image"
          >
            {preview ? (
              <img
                src={preview}
                alt="Ảnh tham chiếu xem trước"
                onError={() => {
                  setError("Không đọc được ảnh đã chọn.");
                  setFile(null);
                  setPreview(null);
                }}
              />
            ) : (
              <span className="upload-icon">
                <Icon kind="image" />
              </span>
            )}
            <span>
              <strong>{file ? file.name : "Thêm ảnh tham chiếu"}</strong>
              <small>
                {file
                  ? "Ảnh dùng cho truy vấn; không tự thêm vào dataset."
                  : "Không bắt buộc · JPEG, PNG, WebP · Tối đa 20 MiB"}
              </small>
            </span>
            <span className="upload-action">
              {file ? "Đổi ảnh" : "Chọn ảnh"} ↗
            </span>
            <input
              id="reference-image"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                chooseFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
          {file && (
            <button
              className="text-button"
              type="button"
              onClick={() => chooseFile()}
            >
              Bỏ ảnh tham chiếu
            </button>
          )}
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </form>
        <p id="search-unavailable" className="availability-note">
          <span className="note-symbol">i</span>{" "}
          {available
            ? "Tìm bằng văn bản, ảnh hoặc kết hợp. Điểm xếp hạng không phải xác suất; điều kiện chưa xác minh sẽ được ghi rõ."
            : "Tìm kiếm chưa sẵn sàng. Kiểm tra model và active index."}
        </p>
      </section>
      <section className="results-section" aria-labelledby="results-heading">
        {results?.query_analysis && (
          <p className="availability-note" data-testid="query-analysis">
            Phân tích theo mẫu: {results.query_analysis.query_type} ·{" "}
            {results.query_analysis.language}
            {results.query_analysis.uncertain
              ? " · Phân tích chưa chắc chắn"
              : ""}{" "}
            · {results.effective_settings?.route}
          </p>
        )}
        <div className="section-title">
          <h2 id="results-heading">Kết quả tìm kiếm</h2>
          <span>
            {loading
              ? "Đang tìm…"
              : results
                ? `${results.total_results} kết quả · ${results.latency.processing_ms.toFixed(1)} ms xử lý`
                : "Chưa có kết quả"}
          </span>
        </div>
        {results && results.results.length > 0 ? (
          <>
            <ExplanationPanel
              key={results.query_id}
              results={results}
              token={resultToken}
              query={query}
            />
            <div className="result-grid">
              {results.results.map((result) => (
                <article
                  className="result-card"
                  id={`image-${result.image_id}`}
                  key={`${results.query_id}-${result.image_id}`}
                >
                  <ResultImage
                    url={result.thumbnail_url}
                    token={resultToken}
                    alt={
                      result.metadata.title ??
                      `Ảnh ${result.image_id.slice(0, 8)}`
                    }
                  />
                  <div className="result-description">
                    <h3>
                      {result.metadata.title ??
                        `Ảnh ${result.image_id.slice(0, 8)}`}
                    </h3>
                    <p>{result.metadata.caption ?? "Chưa có chú thích"}</p>
                    <span>
                      {result.score_type === "cosine"
                        ? "Cosine"
                        : result.score_type === "rrf"
                          ? "RRF"
                          : "Điểm xếp hạng"}{" "}
                      {result.score.toFixed(
                        result.score_type === "rrf" ? 5 : 3,
                      )}
                    </span>
                    <small>{result.metadata.tags.join(", ")}</small>
                    {result.constraint_assessments?.length > 0 && (
                      <ul className="constraint-evidence">
                        {result.constraint_assessments.map((a) => (
                          <li key={a.clause_id}>
                            {a.clause_id}:{" "}
                            {a.status === "unknown"
                              ? "Chưa xác minh"
                              : a.status === "satisfied"
                                ? "Metadata khớp"
                                : "Metadata không khớp"}
                            {a.semantic_score != null
                              ? ` · cosine ${a.semantic_score.toFixed(3)}`
                              : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-results" role="status">
            {loading ? (
              <>
                <span className="spinner" /> Đang tìm ảnh…
              </>
            ) : (
              <>
                <span className="empty-icon">
                  <Icon kind="layers" />
                </span>
                <h3>
                  {results
                    ? "Không tìm thấy ảnh phù hợp."
                    : "Một không gian cho những điều bạn tìm."}
                </h3>
                <p>
                  {results
                    ? "Thử truy vấn khác."
                    : "Nhập token và bắt đầu bằng lời mô tả hoặc ảnh tham chiếu."}
                </p>
              </>
            )}
          </div>
        )}
        {results?.warnings.map((w) => (
          <p className="availability-note" key={w.code}>
            {w.message}
          </p>
        ))}
      </section>
    </>
  );
}
