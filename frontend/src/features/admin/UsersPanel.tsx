import { useCallback, useState } from "react";
import type { AdminUser, CatalogDataset } from "../../types/access";
import { adminAPI } from "./api";
import { useAdminData } from "./useAdminData";
import { useAdminAction } from "./useAdminAction";
import { AdminFeedback } from "./AdminFeedback";

function UserEditor({
  user,
  datasets,
  refresh,
}: {
  user: AdminUser;
  datasets: CatalogDataset[];
  refresh: () => Promise<unknown>;
}) {
  const [role, setRole] = useState(user.role);
  const [active, setActive] = useState(user.is_active);
  const [name, setName] = useState(user.display_name);
  const [grants, setGrants] = useState(user.dataset_ids);
  const [password, setPassword] = useState("");
  const action = useAdminAction();
  return (
    <details className="user-editor">
      <summary>
        <span>
          <strong>{user.display_name}</strong>
          <small>
            @{user.username}
            {user.is_demo ? " · Trải nghiệm" : ""}
          </small>
        </span>
        <span className={`pill ${user.is_active ? "" : "warning"}`}>
          {user.is_active
            ? user.role === "admin"
              ? "Quản trị viên"
              : "Thành viên"
            : "Đã khóa"}
        </span>
      </summary>
      <div className="editor-body">
        <div className="form-grid">
          <label>
            Tên hiển thị
            <input
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Vai trò
            <select
              disabled={user.is_demo}
              value={role}
              onChange={(e) => setRole(e.target.value as "user" | "admin")}
            >
              <option value="user">Thành viên</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
            />
            Cho phép đăng nhập
          </label>
        </div>
        <button
          className="secondary-button"
          disabled={action.busy || !name.trim()}
          onClick={() =>
            void action.run(
              () =>
                adminAPI.updateUser(user.id, {
                  display_name: name.trim(),
                  role,
                  is_active: active,
                }),
              "Đã lưu tài khoản. Thay đổi vai trò hoặc khóa sẽ kết thúc các phiên cũ.",
              refresh,
            )
          }
        >
          Lưu tài khoản
        </button>
        <button
          className="secondary-button"
          disabled={action.busy}
          onClick={() =>
            void action.run(
              () => adminAPI.revokeSessions(user.id),
              "Đã đăng xuất tài khoản khỏi mọi thiết bị. Người dùng có thể đăng nhập lại bằng mật khẩu hiện tại.",
              refresh,
            )
          }
        >
          Đăng xuất mọi thiết bị
        </button>
        <fieldset className="grant-fieldset">
          <legend>Thư viện được truy cập</legend>
          {role === "admin" ? (
            <p>Quản trị viên truy cập toàn bộ thư viện.</p>
          ) : (
            <>
              {datasets.map((d) => (
                <label key={d.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={Boolean(
                      d.is_public ||
                      d.shared_with_members ||
                      grants.includes(d.id),
                    )}
                    disabled={
                      action.busy || d.shared_with_members || d.is_public
                    }
                    onChange={(e) =>
                      setGrants(
                        e.target.checked
                          ? [...grants, d.id]
                          : grants.filter((id) => id !== d.id),
                      )
                    }
                  />
                  {d.name}
                  {d.is_public
                    ? " (công khai)"
                    : d.shared_with_members && " (chung cho thành viên)"}
                  {!d.is_active && " (tạm dừng)"}
                </label>
              ))}
              <p className="muted">
                Thư viện chung được cấp tự động. Các lựa chọn còn lại là quyền
                cấp riêng.
              </p>
              {!datasets.length && <p>Hãy tạo thư viện trước khi cấp quyền.</p>}
              <button
                className="secondary-button"
                disabled={action.busy}
                onClick={() =>
                  void action.run(
                    () => adminAPI.grants(user.id, grants),
                    "Đã cập nhật quyền thư viện.",
                    refresh,
                  )
                }
              >
                Lưu quyền thư viện
              </button>
            </>
          )}
        </fieldset>
        <form
          className="inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              await action.run(
                () => adminAPI.password(user.id, password),
                "Đã đặt mật khẩu mới và kết thúc các phiên cũ.",
              )
            )
              setPassword("");
          }}
        >
          <label>
            Mật khẩu mới
            <input
              type="password"
              minLength={12}
              maxLength={128}
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button className="secondary-button" disabled={action.busy}>
            Đặt lại mật khẩu
          </button>
        </form>
        <AdminFeedback error={action.error} message={action.message} />
      </div>
    </details>
  );
}
export function UsersPanel() {
  const [offset, setOffset] = useState(0);
  const data = useAdminData(
    useCallback(async () => {
      const [users, datasets] = await Promise.all([
        adminAPI.users(offset),
        adminAPI.datasets(),
      ]);
      return { ...users, datasets };
    }, [offset]),
  );
  const action = useAdminAction();
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  return (
    <>
      <div className="panel-heading">
        <div>
          <h2>Tài khoản & quyền truy cập</h2>
          <p>Tạo tài khoản, cấp thư viện và quản lý phiên đăng nhập.</p>
        </div>
        <button
          className="secondary-button"
          disabled={data.loading}
          onClick={() => void data.refresh()}
        >
          Làm mới
        </button>
      </div>
      <details className="admin-card">
        <summary>Tạo tài khoản mới</summary>
        <form
          className="stack-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              await action.run(
                () =>
                  adminAPI.createUser({
                    username,
                    display_name: name,
                    password,
                    role,
                  }),
                "Đã tạo tài khoản. Hãy cấp thư viện cho thành viên mới.",
                data.refresh,
              )
            ) {
              setUsername("");
              setName("");
              setPassword("");
            }
          }}
        >
          <div className="form-grid">
            <label>
              Tên đăng nhập
              <input
                required
                pattern="[a-zA-Z0-9][a-zA-Z0-9_.@+\-]*"
                minLength={3}
                maxLength={120}
                autoComplete="off"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Tên hiển thị
              <input
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              Mật khẩu (ít nhất 12 ký tự)
              <input
                required
                minLength={12}
                maxLength={128}
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              Vai trò
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="user">Thành viên</option>
                <option value="admin">Quản trị viên</option>
              </select>
            </label>
          </div>
          <button className="primary-button" disabled={action.busy}>
            Tạo tài khoản
          </button>
          <AdminFeedback error={action.error} message={action.message} />
        </form>
      </details>
      <AdminFeedback loading={data.loading} error={data.error} />
      {data.data?.rows.map((user) => (
        <UserEditor
          key={user.id}
          user={user}
          datasets={data.data?.datasets ?? []}
          refresh={data.refresh}
        />
      ))}
      {data.data && (
        <div className="pagination">
          <button
            disabled={!offset || data.loading}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            Trước
          </button>
          <span>
            {data.data.total} tài khoản · Trang {Math.floor(offset / 50) + 1}
          </span>
          <button
            disabled={offset + 50 >= data.data.total || data.loading}
            onClick={() => setOffset(offset + 50)}
          >
            Sau
          </button>
        </div>
      )}
    </>
  );
}
