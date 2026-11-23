import { useState } from "react";
import type { AccountRole } from "../../types/access";
import { RegistrationForm } from "./RegistrationForm";
import { LoginCollage } from "./LoginCollage";

export function LoginPage({
  login,
  error,
  retry,
  operatorEnabled,
  quickRoles = [],
  quickLogin,
  successNotice,
}: {
  login: (username: string, password: string) => Promise<void>;
  quickRoles?: AccountRole[];
  quickLogin?: (role: AccountRole) => Promise<void>;
  successNotice?: string;
  error: string | null;
  retry: () => void;
  operatorEnabled: boolean;
}) {
  const [registering, setRegistering] = useState(false);
  const [notice, setNotice] = useState<string | null>(successNotice ?? null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [quickRole, setQuickRole] = useState<AccountRole | null>(null);
  const [issue, setIssue] = useState<string | null>(null);
  const [motionPaused, setMotionPaused] = useState(false);
  return (
    <main
      className={`login-page travel-login collage-login${registering ? " is-registering" : ""}`}
      data-motion={motionPaused ? "paused" : "playing"}
    >
      <LoginCollage />
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-form-wrap">
          <a className="brand" href="/" aria-label="Synlens trang chủ">
            <span className="brand-mark synlens-mark">
              <img src="/branding/synlens-logo.png" alt="" />
            </span>
            <span>Synlens</span>
          </a>

          {registering ? (
            <RegistrationForm
              onCancel={() => {
                setRegistering(false);
                requestAnimationFrame(() =>
                  document.getElementById("login-heading")?.focus(),
                );
              }}
              onComplete={(value) => {
                setUsername(value);
                setPassword("");
                setIssue(null);
                setNotice("Tạo tài khoản thành công. Đăng nhập để tiếp tục.");
                setRegistering(false);
                requestAnimationFrame(() =>
                  document.getElementById("login-heading")?.focus(),
                );
              }}
            />
          ) : (
            <>
              <span className="section-eyebrow">CHÀO MỪNG TRỞ LẠI</span>
              <h1 id="login-heading" tabIndex={-1}>
                Đăng nhập vào Synlens
              </h1>
              <p className="muted">
                Một ý tưởng. Nhiều góc nhìn. Khám phá thư viện của bạn.
              </p>
              {notice && (
                <p className="registration-success" role="status">
                  {notice}
                </p>
              )}
              <form
                onSubmit={async (event) => {
                  event.preventDefault();
                  setBusy(true);
                  setIssue(null);
                  try {
                    await login(username.trim().toLowerCase(), password);
                    setPassword("");
                  } catch (problem) {
                    setIssue(
                      problem instanceof Error
                        ? problem.message
                        : "Không đăng nhập được.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <label htmlFor="login-username">Tên đăng nhập</label>
                <input
                  id="login-username"
                  name="username"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                  maxLength={120}
                  disabled={busy}
                  placeholder="Tên đăng nhập của bạn"
                />
                <label htmlFor="login-password">Mật khẩu</label>
                <div className="password-field">
                  <input
                    id="login-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    maxLength={128}
                    disabled={busy}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-controls="login-password"
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword((value) => !value)}
                    disabled={busy}
                  >
                    {showPassword ? "Ẩn" : "Hiện"}
                    <span className="sr-only"> mật khẩu</span>
                  </button>
                </div>
                {(issue || error) && (
                  <div className="form-alert" role="alert">
                    {issue || error}
                    {error && (
                      <button
                        type="button"
                        className="text-button"
                        onClick={retry}
                      >
                        Kiểm tra lại kết nối
                      </button>
                    )}
                  </div>
                )}
                <button
                  className="primary-button login-submit"
                  type="submit"
                  disabled={busy || !username.trim() || !password}
                >
                  {busy ? "Đang đăng nhập…" : "Đăng nhập"}
                </button>
              </form>
              {quickRoles.length > 0 && quickLogin && (
                <section
                  className="quick-login"
                  aria-labelledby="quick-login-heading"
                >
                  <div className="login-divider">
                    <span>hoặc khám phá với tài khoản trải nghiệm</span>
                  </div>
                  <div className="quick-login-heading">
                    <h3 id="quick-login-heading">Đăng nhập nhanh</h3>
                    <span className="pill">Tài khoản trải nghiệm</span>
                  </div>
                  <p>Dùng tài khoản trải nghiệm trên thư viện hiện tại.</p>
                  <div className="quick-login-buttons">
                    {quickRoles.map((role) => (
                      <button
                        key={role}
                        type="button"
                        className={`quick-role-button quick-role-${role}`}
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          setQuickRole(role);
                          setIssue(null);
                          try {
                            await quickLogin(role);
                            setPassword("");
                          } catch (problem) {
                            setIssue(
                              problem instanceof Error
                                ? problem.message
                                : "Chưa đăng nhập nhanh được.",
                            );
                          } finally {
                            setBusy(false);
                            setQuickRole(null);
                          }
                        }}
                      >
                        <span>
                          <strong>
                            {quickRole === role
                              ? "Đang mở…"
                              : role === "admin"
                                ? "Vào nhanh Admin"
                                : "Vào nhanh User"}
                          </strong>
                          <small>
                            {role === "admin"
                              ? "Quản lý thư viện & tài khoản"
                              : "Tìm kiếm & khám phá ảnh"}
                          </small>
                        </span>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              <p className="auth-switch">
                Chưa có tài khoản?{" "}
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setNotice(null);
                    setIssue(null);
                    setPassword("");
                    setShowPassword(false);
                    setRegistering(true);
                    requestAnimationFrame(() =>
                      document.getElementById("login-heading")?.focus(),
                    );
                  }}
                >
                  <span>Đăng ký</span>
                </button>
              </p>
              <p className="login-help">
                Quên mật khẩu? Liên hệ quản trị viên để được hỗ trợ.
              </p>
            </>
          )}
          <button
            type="button"
            className="login-motion-toggle"
            aria-pressed={motionPaused}
            onClick={() => setMotionPaused((value) => !value)}
          >
            <span aria-hidden="true">{motionPaused ? "▷" : "Ⅱ"}</span>
            {motionPaused ? "Bật chuyển động" : "Tạm dừng chuyển động"}
          </button>
          {operatorEnabled && (
            <a className="operator-link" href="/operator">
              Chế độ vận hành kỹ thuật
            </a>
          )}
        </div>
      </section>
    </main>
  );
}
