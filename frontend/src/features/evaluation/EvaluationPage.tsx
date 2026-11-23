import { useEffect, useState } from "react";
import { api } from "../../services/api/client";
import type { EvaluationSummary } from "../../types/api";

export default function EvaluationPage({
  token,
  onTokenChange,
  authenticated = false,
}: {
  authenticated?: boolean;
  token: string;
  onTokenChange: (value: string) => void;
}) {
  const [loadedToken, setLoadedToken] = useState("");
  const [data, setData] = useState<EvaluationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    if (!token && !authenticated) return;
    const timer = setTimeout(() => {
      setData(null);
      setError(null);
      setLoading(true);
      setLoadedToken(token);
      void api
        .evaluation(token, request.signal)
        .then((value) => {
          if (!request.signal.aborted) setData(value);
        })
        .catch((issue) => {
          if (!request.signal.aborted)
            setError(
              issue instanceof Error
                ? issue.message
                : "Không đọc được báo cáo.",
            );
        })
        .finally(() => {
          if (!request.signal.aborted) setLoading(false);
        });
    }, 500);
    return () => {
      clearTimeout(timer);
      request.abort();
    };
  }, [token, attempt, authenticated]);
  return (
    <section className="evaluation-page" aria-labelledby="evaluation-heading">
      <div className="page-eyebrow">ĐÁNH GIÁ HỆ THỐNG</div>
      <h1 id="evaluation-heading">Nhìn vào những gì đã đo.</h1>
      <p>
        Các lần chạy được lưu bởi công cụ benchmark. Số liệu phản ánh dataset và
        điều kiện của từng lần chạy.
      </p>
      {!authenticated && (
        <>
          <label className="field-label" htmlFor="evaluation-token">
            Token truy cập benchmark
          </label>
          <input
            id="evaluation-token"
            type="password"
            value={token}
            autoComplete="off"
            onChange={(event) => onTokenChange(event.target.value)}
          />
        </>
      )}
      <button
        className="diagnostic-button"
        type="button"
        disabled={(!token && !authenticated) || loading}
        onClick={() => setAttempt((n) => n + 1)}
      >
        Làm mới benchmark
      </button>
      {loading && <p role="status">Đang tải kết quả benchmark…</p>}
      {loadedToken === token && error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
      {!token && !authenticated && (
        <p role="status">Nhập token để xem báo cáo riêng tư.</p>
      )}
      {loadedToken === token && data && (
        <>
          <p role="status">
            {data.state === "available"
              ? `${data.experiments.length} lần chạy đã lưu`
              : data.state === "empty"
                ? "Chưa có kết quả benchmark."
                : "Nguồn benchmark chưa được cấu hình hoặc chưa có thư mục kết quả."}
          </p>
          <p className="availability-note">
            Recall@10 và chất lượng câu trả lời: chưa công bố trên dashboard
            này; cần bộ nhãn do người đánh giá xác nhận. Không suy ra chất lượng
            từ độ trễ.
          </p>
          {data.experiments.length > 0 && (
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Bảng kết quả benchmark có thể cuộn"
            >
              <table>
                <caption>
                  Kết quả lịch sử · độ trễ client của các request thành công
                  (ms)
                </caption>
                <thead>
                  <tr>
                    {[
                      "Lần chạy",
                      "Loại",
                      "Request",
                      "HTTP thành công",
                      "Lỗi HTTP",
                      "P90",
                      "P95",
                      "Recall@10",
                    ].map((name) => (
                      <th key={name} scope="col">
                        {name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.experiments.map((item) => (
                    <tr key={`${item.phase}-${item.id}`}>
                      <th scope="row">
                        <span>{item.id}</span>
                        <small>
                          {item.phase} · {item.status}
                        </small>
                      </th>
                      <td>{item.kind}</td>
                      {[
                        item.attempted,
                        item.successful,
                        item.failed,
                        item.p90_ms,
                        item.p95_ms,
                        item.recall_at_10,
                      ].map((value, i) => (
                        <td key={i}>
                          {value === null
                            ? "Chưa đo"
                            : i >= 3
                              ? value.toFixed(2)
                              : value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data.skipped > 0 && (
            <p>
              {data.skipped} artifact không đọc được hoặc vượt giới hạn; không
              dùng trong bảng.
            </p>
          )}
        </>
      )}
    </section>
  );
}
