import { useCallback, useState } from "react";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { useAdminAction } from "./useAdminAction";
import { AdminFeedback } from "./AdminFeedback";
export function KnowledgePanel() {
  const data = useAdminData(useCallback(() => adminAPI.datasets(), []));
  const [dataset, setDataset] = useState("");
  const [text, setText] = useState("");
  const [checked, setChecked] = useState(false);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const action = useAdminAction();
  async function submit(apply: boolean) {
    await action.run(
      async () => {
        const payload: unknown = JSON.parse(text);
        if (!payload || typeof payload !== "object" || Array.isArray(payload))
          throw new Error("Nội dung JSON phải là một gói tri thức.");
        const result = await adminAPI.knowledge(dataset, payload, apply);
        setReport(result);
        setChecked(!apply);
      },
      apply
        ? "Đã nhập tri thức và gắn quyền theo thư viện."
        : "Gói tri thức hợp lệ. Bạn có thể nhập vào thư viện.",
    );
  }
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Tri thức cho tìm kiếm Agent</h2>
          <p>
            Nhập thực thể, quan hệ và liên kết ảnh có trích nguồn, gắn với một
            thư viện.
          </p>
        </div>
      </div>
      <div className="admin-card stack-form">
        <label>
          Thư viện
          <select
            value={dataset}
            required
            onChange={(e) => {
              setDataset(e.target.value);
              setChecked(false);
            }}
          >
            <option value="">Chọn thư viện</option>
            {data.data
              ?.filter((d) => d.is_active)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Gói JSON (tối đa 1 MB)
          <input
            type="file"
            accept="application/json,.json"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file)
                void action.run(async () => {
                  if (file.size > 1_000_000)
                    throw new Error("Gói tri thức vượt 1 MB.");
                  setText(await file.text());
                  setChecked(false);
                }, "Đã đọc file. Hãy kiểm tra trước khi nhập.");
            }}
          />
        </label>
        <label>
          Nội dung
          <textarea
            className="code-input"
            value={text}
            maxLength={1_000_000}
            onChange={(e) => {
              setText(e.target.value);
              setChecked(false);
            }}
            placeholder="Dán gói tri thức có entities, relationships và image_entities"
          />
        </label>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={action.busy || !dataset || !text}
            onClick={() => void submit(false)}
          >
            Kiểm tra gói tri thức
          </button>
          <button
            className="primary-button"
            disabled={action.busy || !checked}
            onClick={() => void submit(true)}
          >
            Nhập vào thư viện
          </button>
        </div>
        <AdminFeedback
          loading={data.loading}
          error={data.error || action.error}
          message={action.message}
        />
        {report && <pre>{JSON.stringify(report, null, 2)}</pre>}
      </div>
    </>
  );
}
