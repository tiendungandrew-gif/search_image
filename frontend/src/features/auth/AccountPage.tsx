import { useState } from "react";
import type { Account } from "../../types/access";
import { authAPI } from "./api";

export default function AccountPage({
  user,
  onChanged,
}: {
  user: Account;
  onChanged: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <section className="account-page">
      <span className="section-eyebrow">KHÔNG GIAN CÁ NHÂN</span>
      <h1>Tài khoản của bạn</h1>
      <p>
        {user.display_name} · @{user.username}
      </p>
      {user.is_demo ? (
        <div className="admin-card">
          <h2>Tài khoản trải nghiệm</h2>
          <p>
            Bạn đang đăng nhập nhanh. Đăng xuất để chọn vai trò khác hoặc dùng
            tài khoản của bạn.
          </p>
        </div>
      ) : (
        <div className="admin-card">
          <h2>Đổi mật khẩu</h2>
          <p className="muted">
            Sau khi đổi, hãy đăng nhập lại trên các thiết bị của bạn.
          </p>
          <form
            className="stack-form"
            onSubmit={async (e) => {
              e.preventDefault();
              if (busy) return;
              setError(null);
              if (password !== confirm) {
                setError("Hai mật khẩu mới chưa khớp.");
                return;
              }
              if (password === current) {
                setError("Mật khẩu mới phải khác mật khẩu hiện tại.");
                return;
              }
              setBusy(true);
              try {
                await authAPI.password(current, password);
                setCurrent("");
                setPassword("");
                setConfirm("");
                onChanged();
              } catch (issue) {
                setError(
                  issue instanceof Error
                    ? issue.message
                    : "Chưa đổi được mật khẩu.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Mật khẩu hiện tại
              <input
                type="password"
                required
                maxLength={128}
                disabled={busy}
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <label>
              Mật khẩu mới
              <input
                type="password"
                required
                minLength={12}
                maxLength={128}
                disabled={busy}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              Nhập lại mật khẩu mới
              <input
                type="password"
                required
                minLength={12}
                maxLength={128}
                disabled={busy}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </label>
            <small>Từ 12 đến 128 ký tự, khác mật khẩu hiện tại.</small>
            {error && (
              <p role="alert" className="form-alert">
                {error}
              </p>
            )}
            <button className="primary-button" disabled={busy}>
              {busy ? "Đang lưu…" : "Lưu mật khẩu"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
