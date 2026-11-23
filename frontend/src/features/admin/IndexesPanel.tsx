import { useCallback, useState } from "react";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { useAdminAction } from "./useAdminAction";
import { AdminFeedback } from "./AdminFeedback";
export function IndexesPanel() {
  const data = useAdminData(useCallback(() => adminAPI.indexes(), []));
  const action = useAdminAction();
  const [model, setModel] = useState("");
  const [version, setVersion] = useState("");
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const models = [
    ...new Map(data.data?.indexes.map((i) => [i.model_id, i]) ?? []).values(),
  ];
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Chỉ mục & tác vụ</h2>
          <p>
            Lập chỉ mục mới, kiểm tra tính nhất quán rồi chuyển sang phục vụ tìm
            kiếm.
          </p>
        </div>
        <button
          className="secondary-button"
          disabled={data.loading || action.busy}
          onClick={() => void data.refresh()}
        >
          Làm mới tiến độ
        </button>
      </div>
      <details className="admin-card">
        <summary>Tạo chỉ mục mới</summary>
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(
              () => adminAPI.createIndex(model, version),
              "Đã tạo chỉ mục. Chọn Lập chỉ mục để xử lý thư viện.",
              data.refresh,
            );
          }}
        >
          <label>
            Model đã đăng ký
            <select
              required
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="">Chọn model</option>
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.model} · {m.dimension} chiều
                </option>
              ))}
            </select>
          </label>
          <label>
            Phiên bản
            <input
              required
              pattern="[a-z0-9_]+"
              maxLength={40}
              placeholder="vd: library_v2"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
          </label>
          <button className="primary-button" disabled={action.busy}>
            Tạo chỉ mục
          </button>
        </form>
      </details>
      <AdminFeedback
        loading={data.loading}
        error={data.error || action.error}
        message={action.message}
      />
      <div className="index-list">
        {data.data?.indexes.map((i) => (
          <article className="admin-card" key={i.id}>
            <div className="panel-heading">
              <h3>{i.version || i.collection}</h3>
              <span className="pill">
                {i.active ? "Đang phục vụ" : i.status}
              </span>
            </div>
            <p>
              {i.model} · {i.dimension} chiều
            </p>
            <small className="break-word">{i.collection}</small>
            <div className="button-row">
              <button
                className="secondary-button"
                disabled={action.busy || i.status !== "building"}
                onClick={() =>
                  void action.run(
                    () => adminAPI.reindex(i.id),
                    "Đã xếp tác vụ lập chỉ mục.",
                    data.refresh,
                  )
                }
              >
                Lập chỉ mục thư viện
              </button>
              <button
                className="secondary-button"
                disabled={action.busy}
                onClick={() =>
                  void action.run(
                    async () => {
                      const value = await adminAPI.verify(i.id);
                      setReport(value);
                      if (value.status !== "pass")
                        throw new Error(
                          "Chỉ mục chưa đạt. Xem báo cáo kiểm tra bên dưới.",
                        );
                    },
                    "Chỉ mục đã vượt kiểm tra nhất quán.",
                    data.refresh,
                  )
                }
              >
                Kiểm tra chỉ mục
              </button>
              <button
                className="primary-button"
                disabled={action.busy || i.active || i.status !== "ready"}
                onClick={() =>
                  void action.run(
                    () => adminAPI.activate(i.id),
                    "Đã chuyển chỉ mục phục vụ tìm kiếm.",
                    data.refresh,
                  )
                }
              >
                Đưa vào sử dụng
              </button>
            </div>
          </article>
        ))}
      </div>
      {report && (
        <details className="admin-card" open>
          <summary>Báo cáo kiểm tra gần nhất</summary>
          <pre>{JSON.stringify(report, null, 2)}</pre>
        </details>
      )}
      <h2>Tác vụ gần đây</h2>
      <div
        className="table-scroll"
        role="region"
        tabIndex={0}
        aria-label="Bảng tác vụ"
      >
        <table>
          <caption>30 tác vụ mới nhất · làm mới để cập nhật</caption>
          <thead>
            <tr>
              <th>Tác vụ</th>
              <th>Loại</th>
              <th>Trạng thái</th>
              <th>Số ảnh</th>
            </tr>
          </thead>
          <tbody>
            {data.data?.jobs.map((j) => (
              <tr key={j.id}>
                <td>
                  <code>{j.id.slice(0, 8)}</code>
                </td>
                <td>{j.kind}</td>
                <td>{j.status}</td>
                <td>{j.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
