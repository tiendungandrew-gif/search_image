import { lazy, Suspense, useCallback } from "react";
import { api } from "../../services/api/client";
import { useWorkspaceStatus } from "../../hooks/useWorkspaceStatus";
import { DatasetStatus } from "../system/DatasetStatus";
import { UsersPanel } from "./UsersPanel";
import { DatasetsPanel } from "./DatasetsPanel";
import { IndexesPanel } from "./IndexesPanel";
import { KnowledgePanel } from "./KnowledgePanel";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { AdminFeedback } from "./AdminFeedback";
import { useState } from "react";
const EvaluationPage = lazy(() => import("../evaluation/EvaluationPage"));
const tabs = [
  ["", "Tổng quan"],
  ["users", "Tài khoản"],
  ["datasets", "Thư viện"],
  ["indexes", "Chỉ mục"],
  ["knowledge", "Tri thức"],
  ["evaluation", "Đánh giá"],
  ["audit", "Nhật ký"],
];
type Navigate = (
  event: React.MouseEvent<HTMLAnchorElement>,
  target: string,
) => void;
function Overview({ navigate }: { navigate: Navigate }) {
  const workspace = useWorkspaceStatus("", true);
  const readiness = useAdminData(useCallback(() => api.readiness(""), []));
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Mọi thứ trong một không gian</h2>
          <p>Theo dõi thư viện, dịch vụ và khả năng tìm kiếm đang hoạt động.</p>
        </div>
        <button
          className="secondary-button"
          onClick={() => {
            void workspace.refresh();
            void readiness.refresh();
          }}
        >
          Làm mới trạng thái
        </button>
      </div>
      <nav
        className="admin-shortcuts"
        aria-label="Thao tác quản trị thường dùng"
      >
        {[
          [
            "/admin/datasets",
            "Thêm và quản lý ảnh",
            "Tạo thư viện, tải ảnh và sửa thông tin.",
          ],
          [
            "/admin/users",
            "Quản lý thành viên",
            "Tạo tài khoản và chia sẻ thư viện.",
          ],
          [
            "/admin/indexes",
            "Theo dõi xử lý ảnh",
            "Xem tác vụ và kiểm tra ảnh đã sẵn sàng.",
          ],
        ].map(([target, label, help]) => (
          <a key={target} href={target} onClick={(e) => navigate(e, target)}>
            <strong>
              {label}
              <span aria-hidden="true"> ↗</span>
            </strong>
            <span>{help}</span>
          </a>
        ))}
      </nav>
      <div className="admin-overview-grid">
        <DatasetStatus
          status={workspace.workspace}
          loading={workspace.loading}
          error={workspace.error}
          refresh={() => void workspace.refresh()}
        />
        <section className="admin-card">
          <h3>Kết nối dịch vụ</h3>
          <AdminFeedback loading={readiness.loading} error={readiness.error} />
          <ul className="service-list">
            {readiness.data &&
              Object.entries(readiness.data.dependencies).map(
                ([name, state]) => (
                  <li key={name}>
                    <span>{name}</span>
                    <span
                      className={
                        state === "healthy" ? "service-ok" : "service-bad"
                      }
                    >
                      {state === "healthy" ? "Sẵn sàng" : "Cần kiểm tra"}
                    </span>
                  </li>
                ),
              )}
          </ul>
        </section>
      </div>
      <div className="admin-card">
        <h3>Bắt đầu với một thư viện</h3>
        <ol className="getting-started">
          <li>Tạo thư viện và thêm ảnh có quyền sử dụng.</li>
          <li>Tạo tài khoản thành viên, cấp quyền vào thư viện.</li>
          <li>Kiểm tra tiến độ chỉ mục trước khi tìm kiếm.</li>
        </ol>
      </div>
    </>
  );
}
function AuditPanel() {
  const [offset, setOffset] = useState(0);
  const data = useAdminData(
    useCallback(() => adminAPI.audit(offset), [offset]),
  );
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Nhật ký quản trị</h2>
          <p>Theo dõi thay đổi tài khoản, dữ liệu và chỉ mục.</p>
        </div>
        <button
          className="secondary-button"
          onClick={() => void data.refresh()}
        >
          Làm mới
        </button>
      </div>
      <AdminFeedback loading={data.loading} error={data.error} />
      <div
        className="table-scroll"
        role="region"
        tabIndex={0}
        aria-label="Bảng nhật ký"
      >
        <table>
          <caption>Các hoạt động được lưu gần đây</caption>
          <thead>
            <tr>
              <th>Thời điểm</th>
              <th>Tài khoản</th>
              <th>Hoạt động</th>
              <th>Đối tượng</th>
            </tr>
          </thead>
          <tbody>
            {data.data?.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.created_at).toLocaleString("vi-VN")}</td>
                <td>{e.actor}</td>
                <td>{e.action}</td>
                <td className="break-word">{e.resource_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <button
          disabled={!offset || data.loading}
          onClick={() => setOffset(Math.max(0, offset - 50))}
        >
          Trước
        </button>
        <span>Trang {Math.floor(offset / 50) + 1}</span>
        <button
          disabled={(data.data?.length ?? 0) < 50 || data.loading}
          onClick={() => setOffset(offset + 50)}
        >
          Sau
        </button>
      </div>
    </>
  );
}
export default function AdminWorkspace({
  path,
  navigate,
}: {
  path: string;
  navigate: (
    event: React.MouseEvent<HTMLAnchorElement>,
    target: string,
  ) => void;
}) {
  const active = path.replace(/^\/admin\/?/, "");
  return (
    <section className="admin-workspace">
      <div className="admin-title">
        <span className="section-eyebrow">LENS STUDIO</span>
        <h1>Không gian quản trị</h1>
        <p>Chăm sóc thư viện. Kết nối những người khám phá.</p>
      </div>
      <nav className="admin-tabs" aria-label="Quản trị">
        {tabs.map(([key, label]) => (
          <a
            key={key}
            href={`/admin${key ? "/" + key : ""}`}
            aria-current={active === key ? "page" : undefined}
            onClick={(e) => navigate(e, `/admin${key ? "/" + key : ""}`)}
          >
            {label}
          </a>
        ))}
      </nav>
      <div className="admin-panel" key={active}>
        {active === "" ? (
          <Overview navigate={navigate} />
        ) : active === "users" ? (
          <UsersPanel />
        ) : active === "datasets" ? (
          <DatasetsPanel />
        ) : active === "indexes" ? (
          <IndexesPanel />
        ) : active === "knowledge" ? (
          <KnowledgePanel />
        ) : active === "audit" ? (
          <AuditPanel />
        ) : active === "evaluation" ? (
          <Suspense fallback={<p role="status">Đang mở đánh giá…</p>}>
            <EvaluationPage
              token=""
              onTokenChange={() => undefined}
              authenticated
            />
          </Suspense>
        ) : (
          <h2>Không tìm thấy trang quản trị</h2>
        )}
      </div>
    </section>
  );
}
