import { useRef, useState } from "react";
import { authAPI } from "./api";

export function RegistrationForm({
  onComplete,
  onCancel,
}: {
  onComplete: (username: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [issue, setIssue] = useState<string | null>(null);
  const confirmInput = useRef<HTMLInputElement>(null);
  return (
    <>
      <div className="signup-heading">
        <span className="signup-badge">
          <span aria-hidden="true" /> KHÔNG GIAN CHO Ý TƯỞNG CỦA BẠN
        </span>
        <h1 id="login-heading" tabIndex={-1}>
          Tạo tài khoản Synlens
        </h1>
        <p className="muted">Lưu giữ cảm hứng. Khám phá những góc nhìn mới.</p>
      </div>
      <form
        className="registration-form"
        aria-label="Đăng ký tài khoản"
        onSubmit={async (event) => {
          event.preventDefault();
          if (busy) return;
          setIssue(null);
          if (password !== confirmation) {
            setIssue("Mật khẩu xác nhận chưa khớp.");
            confirmInput.current?.focus();
            return;
          }
          setBusy(true);
          try {
            const normalized = username.trim().toLowerCase();
            await authAPI.register(name.trim(), normalized, password);
            setPassword("");
            setConfirmation("");
            onComplete(normalized);
          } catch (error) {
            setIssue(
              error instanceof Error
                ? error.message
                : "Chưa đăng ký được. Vui lòng thử lại.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <fieldset className="signup-section">
          <legend>
            <span className="signup-section-marker" aria-hidden="true">
              01
            </span>{" "}
            Thông tin cá nhân
          </legend>
          <div className="signup-identity-grid">
            <div className="signup-field">
              <label htmlFor="register-name">Tên hiển thị</label>
              <input
                id="register-name"
                placeholder="Tên của bạn"
                name="name"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                disabled={busy}
              />
            </div>
            <div className="signup-field">
              <label htmlFor="register-username">Tên đăng nhập</label>
              <input
                id="register-username"
                placeholder="vd: minhanh"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                maxLength={120}
                pattern="[a-zA-Z0-9][a-zA-Z0-9_.@+\-]*"
                aria-describedby="register-username-hint"
                disabled={busy}
              />
            </div>
          </div>
          <p className="registration-hint" id="register-username-hint">
            Tên đăng nhập từ 3 ký tự: chữ Latin, số hoặc . _ @ + -
          </p>
        </fieldset>
        <fieldset className="signup-section">
          <legend>
            <span className="signup-section-marker" aria-hidden="true">
              02
            </span>{" "}
            Bảo mật tài khoản
          </legend>
          <div className="signup-field">
            <label htmlFor="register-password">Mật khẩu</label>
            <div className="password-field">
              <input
                id="register-password"
                name="password"
                autoComplete="new-password"
                type={visible ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setIssue(null);
                }}
                required
                minLength={12}
                maxLength={128}
                aria-describedby="register-password-hint"
                disabled={busy}
              />
              <button
                type="button"
                className="password-toggle"
                aria-controls="register-password register-confirm"
                aria-pressed={visible}
                onClick={() => setVisible((v) => !v)}
                disabled={busy}
              >
                {visible ? "Ẩn" : "Hiện"}
                <span className="sr-only"> mật khẩu</span>
              </button>
            </div>
          </div>
          <div className="signup-field">
            <label htmlFor="register-confirm">Xác nhận mật khẩu</label>
            <input
              ref={confirmInput}
              id="register-confirm"
              name="confirmation"
              autoComplete="new-password"
              type={visible ? "text" : "password"}
              value={confirmation}
              onChange={(e) => {
                setConfirmation(e.target.value);
                setIssue(null);
              }}
              required
              minLength={12}
              maxLength={128}
              disabled={busy}
            />
          </div>
          <div className="signup-checks" id="register-password-hint">
            <span className={password.length >= 12 ? "is-valid" : ""}>
              <span aria-hidden="true">
                {password.length >= 12 ? "✓" : "○"}
              </span>{" "}
              12–128 ký tự
            </span>
            <span
              className={
                confirmation && confirmation === password ? "is-valid" : ""
              }
            >
              <span aria-hidden="true">
                {confirmation && confirmation === password ? "✓" : "○"}
              </span>{" "}
              Mật khẩu khớp
            </span>
          </div>
        </fieldset>
        {issue && (
          <p className="form-alert" role="alert">
            {issue}
          </p>
        )}
        <div className="signup-access-note">
          <svg
            aria-hidden="true"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" />
            <path d="m8 12 3 3 5-6" />
          </svg>
          <p>
            Dùng ngay các thư viện chung cho thành viên.
            <small>Thư viện riêng được quản trị viên cấp quyền bổ sung.</small>
          </p>
        </div>
        <button
          className="primary-button login-submit"
          disabled={
            busy ||
            !name.trim() ||
            !username.trim() ||
            !password ||
            !confirmation
          }
          type="submit"
        >
          {busy ? "Đang tạo tài khoản…" : "Tạo tài khoản"}
        </button>
      </form>
      <p className="auth-switch">
        Đã có tài khoản?{" "}
        <button type="button" onClick={onCancel} disabled={busy}>
          <span>Đăng nhập</span>
        </button>
      </p>
    </>
  );
}
