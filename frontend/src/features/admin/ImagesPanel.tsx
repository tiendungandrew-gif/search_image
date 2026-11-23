import { useCallback, useState } from "react";
import type { AdminImage, CatalogDataset } from "../../types/access";
import { ResultImage } from "../search/ResultImage";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { useAdminAction } from "./useAdminAction";
import { AdminFeedback } from "./AdminFeedback";
function ImageEditor({
  image,
  datasets,
  refresh,
}: {
  image: AdminImage;
  datasets: CatalogDataset[];
  refresh: () => Promise<unknown>;
}) {
  const [title, setTitle] = useState(image.title ?? "");
  const [caption, setCaption] = useState(image.caption ?? "");
  const [tags, setTags] = useState(image.tags.join(", "));
  const [dataset, setDataset] = useState(
    datasets.find((d) => d.key === image.source_dataset)?.id ?? "",
  );
  const action = useAdminAction();
  return (
    <article className="admin-image">
      <div className="admin-image-preview">
        {image.hidden ? (
          <span>Ảnh đang ẩn</span>
        ) : (
          <ResultImage
            url={image.thumbnail_url}
            alt={image.title ?? "Ảnh trong thư viện"}
            token=""
          />
        )}
      </div>
      <div className="admin-image-body">
        <h3>{image.title || "Ảnh chưa có tên"}</h3>
        <small>
          {image.width} × {image.height} · {image.status}
        </small>
        <details>
          <summary>Sửa thông tin ảnh</summary>
          <form
            className="stack-form"
            onSubmit={(e) => {
              e.preventDefault();
              void action.run(
                () =>
                  adminAPI.editImage(image.id, {
                    title: title || null,
                    caption: caption || null,
                    tags: tags
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean),
                    dataset_id: dataset,
                  }),
                "Đã lưu. Ảnh trở lại tìm kiếm sau khi cập nhật chỉ mục.",
                refresh,
              );
            }}
          >
            <label>
              Tiêu đề
              <input
                maxLength={256}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Mô tả
              <textarea
                maxLength={4000}
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
              />
            </label>
            <label>
              Thẻ (cách nhau bằng dấu phẩy)
              <input value={tags} onChange={(e) => setTags(e.target.value)} />
            </label>
            <label>
              Thư viện
              <select
                required
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
              >
                <option value="">Chọn thư viện</option>
                {datasets
                  .filter((d) => d.is_active && d.key !== "__unassigned__")
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
              </select>
            </label>
            <button
              className="secondary-button"
              disabled={action.busy || !dataset}
            >
              Lưu & cập nhật chỉ mục
            </button>
          </form>
        </details>
        <button
          className="quiet-button"
          disabled={action.busy}
          onClick={() =>
            void action.run(
              () => adminAPI.moderate(image.id, !image.hidden),
              image.hidden
                ? "Đã khôi phục ảnh vào tìm kiếm."
                : "Đã ẩn ảnh. Ảnh gốc được giữ lại.",
              refresh,
            )
          }
        >
          {image.hidden ? "Khôi phục ảnh" : "Ẩn khỏi tìm kiếm"}
        </button>
        <AdminFeedback error={action.error} message={action.message} />
      </div>
    </article>
  );
}
export function ImagesPanel({
  datasets,
  onChanged,
}: {
  datasets: CatalogDataset[];
  onChanged: () => Promise<unknown>;
}) {
  const [dataset, setDataset] = useState("");
  const [offset, setOffset] = useState(0);
  const data = useAdminData(
    useCallback(() => adminAPI.images(dataset, offset), [dataset, offset]),
  );
  const action = useAdminAction();
  const [uploadDataset, setUploadDataset] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [license, setLicense] = useState("");
  const [rights, setRights] = useState("");
  const refreshData = data.refresh;
  const refresh = useCallback(async () => {
    await refreshData();
    await onChanged();
  }, [refreshData, onChanged]);
  return (
    <section className="image-management">
      <div className="panel-heading">
        <h2>Hình ảnh</h2>
        <label>
          Lọc thư viện
          <select
            value={dataset}
            onChange={(e) => {
              setDataset(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Tất cả thư viện</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <details className="admin-card">
        <summary>Thêm ảnh vào thư viện</summary>
        <form
          className="stack-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!file) return;
            if (file.size > 20 * 1024 * 1024) {
              await action.run(
                () => Promise.reject(new Error("Ảnh vượt 20 MB.")),
                "",
              );
              return;
            }
            if (
              await action.run(
                () =>
                  adminAPI.upload(
                    file,
                    uploadDataset,
                    { title: title || null, license, rights_ref: rights },
                    crypto.randomUUID(),
                  ),
                "Đã tiếp nhận ảnh; theo dõi tiến độ trong mục Chỉ mục.",
                refresh,
              )
            ) {
              setTitle("");
            }
          }}
        >
          <div className="form-grid">
            <label>
              Ảnh (JPEG, PNG, WebP; tối đa 20 MB)
              <input
                required
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <label>
              Thư viện đích
              <select
                required
                value={uploadDataset}
                onChange={(e) => setUploadDataset(e.target.value)}
              >
                <option value="">Chọn thư viện</option>
                {datasets
                  .filter((d) => d.is_active && d.key !== "__unassigned__")
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Tiêu đề
              <input
                maxLength={256}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Giấy phép
              <input
                required
                maxLength={256}
                placeholder="vd: CC-BY-4.0"
                value={license}
                onChange={(e) => setLicense(e.target.value)}
              />
            </label>
            <label>
              Nguồn / quyền sử dụng
              <input
                required
                maxLength={1000}
                placeholder="Nguồn ảnh hoặc xác nhận quyền sở hữu"
                value={rights}
                onChange={(e) => setRights(e.target.value)}
              />
            </label>
          </div>
          <button
            className="primary-button"
            disabled={action.busy || !file || !uploadDataset}
          >
            Tải lên & lập chỉ mục
          </button>
          <AdminFeedback error={action.error} message={action.message} />
        </form>
      </details>
      <AdminFeedback loading={data.loading} error={data.error} />
      <div className="admin-image-grid">
        {data.data?.rows.map((image) => (
          <ImageEditor
            key={`${image.id}:${image.hidden}:${image.title}:${image.caption}:${image.source_dataset}`}
            image={image}
            datasets={datasets}
            refresh={refresh}
          />
        ))}
      </div>
      {data.data && (
        <div className="pagination">
          <button
            disabled={!offset || data.loading}
            onClick={() => setOffset(Math.max(0, offset - 30))}
          >
            Trước
          </button>
          <span>
            {data.data.total} ảnh · Trang {Math.floor(offset / 30) + 1}
          </span>
          <button
            disabled={offset + 30 >= data.data.total || data.loading}
            onClick={() => setOffset(offset + 30)}
          >
            Sau
          </button>
        </div>
      )}
    </section>
  );
}
