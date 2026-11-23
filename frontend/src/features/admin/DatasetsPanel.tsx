import { useCallback, useState } from "react";
import type { CatalogDataset } from "../../types/access";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { useAdminAction } from "./useAdminAction";
import { AdminFeedback } from "./AdminFeedback";
import { ImagesPanel } from "./ImagesPanel";
function DatasetEditor({
  dataset,
  refresh,
}: {
  dataset: CatalogDataset;
  refresh: () => Promise<unknown>;
}) {
  const [name, setName] = useState(dataset.name);
  const [description, setDescription] = useState(dataset.description);
  const [active, setActive] = useState(dataset.is_active);
  const [shared, setShared] = useState(dataset.shared_with_members);
  const [isPublic, setPublic] = useState(Boolean(dataset.is_public));
  const action = useAdminAction();
  return (
    <details className="dataset-tile">
      <summary>
        <span className="dataset-monogram" aria-hidden="true">
          {dataset.name.slice(0, 1)}
        </span>
        <span>
          <strong>{dataset.name}</strong>
          <small>
            {dataset.images} ảnh ·{" "}
            {dataset.is_active ? "Đang hoạt động" : "Tạm dừng"} ·{" "}
            {dataset.is_public
              ? "Công khai cho khách"
              : dataset.shared_with_members
                ? "Chung cho thành viên"
                : "Cấp quyền riêng"}
          </small>
        </span>
      </summary>
      <form
        className="stack-form"
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(
            () =>
              adminAPI.updateDataset(dataset.id, {
                name: name.trim(),
                description,
                is_active: active,
                shared_with_members: shared,
                is_public: isPublic,
              }),
            "Đã cập nhật thư viện.",
            refresh,
          );
        }}
      >
        <label>
          Tên thư viện
          <input
            required
            maxLength={128}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Mô tả
          <textarea
            maxLength={1000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          Thư viện đang hoạt động
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={shared}
            disabled={action.busy}
            onChange={(e) => setShared(e.target.checked)}
          />
          Chia sẻ cho mọi thành viên
        </label>
        <p className="muted">
          User mới được tìm và xem ảnh ngay khi đăng nhập. Chỉ Admin được thêm,
          sửa hoặc ẩn ảnh. Quyền thành viên khác với quyền công khai bên dưới.
        </p>
        <p className="muted">
          Bỏ chia sẻ chung sẽ giữ lại các quyền đã cấp riêng cho từng tài khoản.
        </p>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={isPublic}
            disabled={action.busy}
            onChange={(e) => setPublic(e.target.checked)}
          />
          Công khai cho khách (không cần đăng nhập)
        </label>
        <p className="muted">
          Mọi người đều có thể tìm, xem và mở ảnh trong thư viện công khai. Tắt
          mục này để thu hồi quyền khách; quyền thành viên và quyền cấp riêng
          vẫn được giữ.
        </p>
        <small>Mã thư viện: {dataset.key}</small>
        <button className="secondary-button" disabled={action.busy}>
          Lưu thư viện
        </button>
        <AdminFeedback error={action.error} message={action.message} />
      </form>
    </details>
  );
}
export function DatasetsPanel() {
  const data = useAdminData(useCallback(() => adminAPI.datasets(), []));
  const action = useAdminAction();
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [shared, setShared] = useState(false);
  const [isPublic, setPublic] = useState(false);
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Thư viện & hình ảnh</h2>
          <p>
            Quản lý thư viện công khai, chung cho thành viên và cấp quyền riêng.
          </p>
        </div>
        <button
          className="secondary-button"
          onClick={() => void data.refresh()}
        >
          Làm mới
        </button>
      </div>
      <details className="admin-card">
        <summary>Tạo thư viện</summary>
        <form
          className="inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              await action.run(
                () =>
                  adminAPI.createDataset({
                    name: name.trim(),
                    key,
                    shared_with_members: shared,
                    is_public: isPublic,
                  }),
                "Đã tạo thư viện.",
                data.refresh,
              )
            ) {
              setName("");
              setKey("");
              setShared(false);
              setPublic(false);
            }
          }}
        >
          <label>
            Tên thư viện
            <input
              required
              maxLength={128}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Mã thư viện
            <input
              required
              pattern="[a-zA-Z0-9][a-zA-Z0-9_.@+\-]*"
              maxLength={128}
              placeholder="vd: travel-2026"
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={shared}
              disabled={action.busy}
              onChange={(e) => setShared(e.target.checked)}
            />
            Chia sẻ cho mọi thành viên
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isPublic}
              disabled={action.busy}
              onChange={(e) => setPublic(e.target.checked)}
            />
            Công khai cho khách (không cần đăng nhập)
          </label>
          <button className="primary-button" disabled={action.busy}>
            Tạo thư viện
          </button>
        </form>
        <AdminFeedback error={action.error} message={action.message} />
      </details>
      <AdminFeedback loading={data.loading} error={data.error} />
      <div className="dataset-grid">
        {data.data?.map((d) => (
          <DatasetEditor
            key={`${d.id}:${d.is_active}:${d.shared_with_members}:${d.is_public}:${d.name}:${d.description}`}
            dataset={d}
            refresh={data.refresh}
          />
        ))}
      </div>
      {data.data && (
        <ImagesPanel datasets={data.data} onChanged={data.refresh} />
      )}
    </>
  );
}
