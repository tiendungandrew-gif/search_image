import type { WorkspaceStatus } from "../../types/api";

const labels = {
  empty_dataset: "Chưa có dữ liệu ảnh",
  index_building: "Đang xây chỉ mục",
  index_not_ready: "Chỉ mục chưa sẵn sàng",
  ready: "Dataset sẵn sàng",
  unavailable: "Chưa kiểm tra được dữ liệu",
};
export function DatasetStatus({
  status,
  loading,
  error,
  refresh,
}: {
  status: WorkspaceStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}) {
  return (
    <section
      className="connection-card dataset-card"
      aria-labelledby="dataset-heading"
    >
      <div className="sidebar-title">
        <h2 id="dataset-heading">Dữ liệu & khả năng</h2>
        <span
          className={`status-dot ${status?.dataset.state === "ready" ? "ready-dot" : ""}`}
        />
      </div>
      <div role="status" data-testid="dataset-status">
        <h3>
          {status
            ? labels[status.dataset.state]
            : loading
              ? "Đang kiểm tra dataset…"
              : "Chưa xác minh dataset"}
        </h3>
        {!status && (
          <p className="sidebar-description">
            Nhập token để đọc trạng thái riêng tư từ backend.
          </p>
        )}
        {error && <p className="error-message">{error}</p>}
        {status && (
          <>
            <dl className="dataset-counts">
              <div>
                <dt>Ảnh trong DB</dt>
                <dd>{status.dataset.images ?? "Chưa biết"}</dd>
              </div>
              <div>
                <dt>Đã lập chỉ mục</dt>
                <dd>{status.dataset.indexed_images ?? "Chưa biết"}</dd>
              </div>
              <div>
                <dt>Vector quan sát</dt>
                <dd>{status.dataset.vectors ?? "Chưa biết"}</dd>
              </div>
            </dl>
            {status.dataset.state === "empty_dataset" && (
              <p>
                Chưa có ảnh để tìm kiếm. Nhập dữ liệu theo README, chạy indexing
                rồi làm mới tại đây.
              </p>
            )}
            {status.dataset.state === "index_building" && (
              <p>Dữ liệu đang được xử lý. Trạng thái cập nhật mỗi 30 giây.</p>
            )}
            {status.dataset.state === "index_not_ready" && (
              <p>
                Kiểm tra model, index đang hoạt động và các receipt indexing.
              </p>
            )}
            {status.dataset.state === "unavailable" && (
              <p>Chưa xác định được dữ liệu; kiểm tra kết nối dịch vụ.</p>
            )}
            <ul className="capability-list">
              <li>
                Semantic:{" "}
                {status.capabilities.text_search ? "Sẵn sàng" : "Chưa sẵn sàng"}
              </li>
              <li>
                RAG:{" "}
                {status.capabilities.explanations
                  ? "Sẵn sàng"
                  : status.rag.enabled
                    ? "Chưa cấu hình được LLM"
                    : "Đang tắt"}
              </li>
              <li>
                Agent:{" "}
                {status.capabilities.agent
                  ? "Sẵn sàng"
                  : status.agent.enabled
                    ? "Chưa sẵn sàng"
                    : "Đang tắt"}
              </li>
              <li>
                LLM planner:{" "}
                {status.agent.llm_planning ? "Đã cấu hình" : "Chưa khả dụng"}
              </li>
            </ul>
          </>
        )}
      </div>
      <button
        className="diagnostic-button"
        type="button"
        disabled={loading}
        onClick={refresh}
      >
        {loading ? "Đang đọc trạng thái…" : "Làm mới dataset"}
      </button>
    </section>
  );
}
