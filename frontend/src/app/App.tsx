import { CurrentAccountContext } from "../features/auth/CurrentAccountContext";
import { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar } from "../features/chat/Sidebar";
import { FavoritesProvider } from "../features/profile/FavoritesProvider";
import { Icon } from "../components/Icon";
import { SearchWorkspace } from "../features/search/SearchWorkspace";
import { AccountMenu } from "../features/auth/AccountMenu";
import { LoginPage } from "../features/auth/LoginPage";
import { useAuth } from "../features/auth/useAuth";
import { useHealth } from "../hooks/useHealth";
import { useWorkspaceStatus } from "../hooks/useWorkspaceStatus";
const AdminWorkspace = lazy(() => import("../features/admin/AdminWorkspace"));
const ProfilePage = lazy(() => import("../features/profile/ProfilePage"));
const FavoritesPage = lazy(() => import("../features/profile/FavoritesPage"));
const AccountPage = lazy(() => import("../features/auth/AccountPage"));
const OperatorWorkspace = lazy(() =>
  import("../features/operator/OperatorWorkspace").then((m) => ({
    default: m.OperatorWorkspace,
  })),
);

export function App() {
  const auth = useAuth();
  const { health } = useHealth();
  const [path, setPath] = useState(location.pathname);
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("lens.theme") === "dark";
    } catch {
      return false;
    }
  });
  const [passwordChanged, setPasswordChanged] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [searchHost, setSearchHost] = useState<HTMLDivElement | null>(null);
  const workspace = useWorkspaceStatus(
    "",
    Boolean(auth.user),
    auth.user
      ? `${auth.user.id}:${auth.user.role}:${auth.user.datasets.map((d) => d.id).join(",")}`
      : "",
    !auth.loading && !auth.user && path === "/",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  useEffect(() => {
    const pop = () => setPath(location.pathname);
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  function navigate(
    event: React.MouseEvent<HTMLAnchorElement>,
    target: string,
  ) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
      return;
    event.preventDefault();
    history.pushState(null, "", target);
    setPath(target);
    window.scrollTo({ top: 0 });
  }
  const userId = auth.user?.id;
  useEffect(() => {
    if (!userId) return;
    const frame = requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>("#main-content h1");
      heading?.setAttribute("tabindex", "-1");
      heading?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [path, userId]);
  if (auth.loading)
    return (
      <main className="session-loading" role="status">
        <span className="spinner" />
        Đang mở không gian của bạn…
      </main>
    );
  if (path.startsWith("/operator") && auth.legacy_enabled)
    return (
      <Suspense fallback={<p role="status">Đang mở công cụ vận hành…</p>}>
        <OperatorWorkspace />
      </Suspense>
    );
  if (!auth.user && path !== "/")
    return (
      <LoginPage
        successNotice={
          passwordChanged
            ? "Đổi mật khẩu thành công. Vui lòng đăng nhập lại bằng mật khẩu mới."
            : undefined
        }
        login={async (username, password) => {
          await auth.login(username, password);
          setPasswordChanged(false);
          history.replaceState(null, "", "/");
          setPath("/");
        }}
        error={auth.error}
        retry={() => void auth.refresh()}
        operatorEnabled={auth.legacy_enabled}
        quickRoles={auth.quick_login_roles}
        quickLogin={async (role) => {
          await auth.quickLogin(role);
          const target = role === "admin" ? "/admin" : "/";
          history.replaceState(null, "", target);
          setPath(target);
          window.scrollTo({ top: 0 });
        }}
      />
    );
  const user = auth.user;
  const guest = !user;
  const identity = user
    ? `${user.id}:${user.role}:${user.datasets
        .map((d) => d.id)
        .sort()
        .join(",")}`
    : "guest";
  const admin = path.startsWith("/admin");
  return (
    <FavoritesProvider
      key={user?.id ?? "guest"}
      enabled={Boolean(user && !user.is_demo)}
      onSignIn={() => {
        const target = user ? "/profile" : "/login";
        history.pushState(null, "", target);
        setPath(target);
      }}
    >
      <CurrentAccountContext.Provider value={user}>
        <div
          className={`app-shell signed-in with-sidebar${["/", "/profile", "/favorites"].includes(path) ? " consumer-site travel-site" : ""}`}
        >
          <a className="skip-link" href="#main-content">
            Đến nội dung chính
          </a>
          <Sidebar
            user={user}
            path={path}
            datasets={
              user?.datasets ?? workspace.workspace?.public_datasets ?? []
            }
            onNavigate={navigate}
          />
          <header className={`app-header${path === "/" ? " has-search" : ""}`}>
            {path === "/" && (
              <div id="header-search-root" ref={setSearchHost} />
            )}
            <div className="account-menu">
              <button
                className="theme-button"
                aria-label={dark ? "Giao diện sáng" : "Giao diện tối"}
                title={
                  dark
                    ? "Chuyển sang giao diện sáng"
                    : "Chuyển sang giao diện tối"
                }
                type="button"
                aria-pressed={dark}
                onClick={() => {
                  setDark(!dark);
                  try {
                    localStorage.setItem("lens.theme", dark ? "light" : "dark");
                  } catch {
                    /* Optional preference. */
                  }
                }}
              >
                <Icon kind={dark ? "sun" : "moon"} />
                <span>{dark ? "Giao diện sáng" : "Giao diện tối"}</span>
              </button>
              {user ? (
                <AccountMenu
                  user={user}
                  onNavigate={navigate}
                  onLogout={() => {
                    setLogoutError(null);
                    void auth
                      .logout()
                      .catch(() =>
                        setLogoutError(
                          "Chưa đăng xuất được. Vui lòng thử lại.",
                        ),
                      );
                  }}
                />
              ) : (
                <a
                  className="guest-signin"
                  href="/login"
                  onClick={(e) => navigate(e, "/login")}
                >
                  Đăng nhập
                </a>
              )}
            </div>
          </header>
          <main id="main-content" tabIndex={-1} key={identity}>
            {logoutError && (
              <p role="alert" className="form-alert">
                {logoutError}
              </p>
            )}
            <Suspense fallback={<p role="status">Đang mở trang…</p>}>
              {admin ? (
                user?.role === "admin" ? (
                  <AdminWorkspace path={path} navigate={navigate} />
                ) : (
                  <section className="empty-results">
                    <h1>Bạn không có quyền quản trị</h1>
                    <p>
                      Liên hệ quản trị viên để được hỗ trợ về tài khoản hoặc thư
                      viện.
                    </p>
                    <a href="/" onClick={(e) => navigate(e, "/")}>
                      Trở về tìm kiếm
                    </a>
                  </section>
                )
              ) : path === "/profile" && user ? (
                <ProfilePage user={user} onSaved={() => void auth.refresh()} />
              ) : path === "/favorites" && user ? (
                <FavoritesPage user={user} />
              ) : path === "/account" && user ? (
                <AccountPage
                  user={user}
                  onChanged={() => {
                    setPasswordChanged(true);
                    window.dispatchEvent(new Event("lens:auth-expired"));
                  }}
                />
              ) : path === "/" ? (
                <SearchWorkspace
                  searchHost={searchHost}
                  token=""
                  onTokenChange={() => undefined}
                  authenticated={Boolean(user)}
                  guest={guest}
                  onRequestLogin={() => {
                    history.pushState(null, "", "/login");
                    setPath("/login");
                    window.scrollTo({ top: 0 });
                  }}
                  showDiagnostics={false}
                  datasets={
                    user?.datasets ?? workspace.workspace?.public_datasets ?? []
                  }
                  available={health?.capabilities.text_search ?? false}
                  agentAvailable={health?.capabilities.agent ?? false}
                  capabilities={
                    guest && health
                      ? {
                          ...health.capabilities,
                          text_search:
                            workspace.workspace?.capabilities.text_search ??
                            false,
                          image_search: false,
                          multimodal: false,
                          multi_intent: false,
                          rerank: false,
                          explanations: false,
                          agent: false,
                        }
                      : health?.capabilities
                  }
                  workspace={workspace.workspace}
                />
              ) : (
                <section className="empty-results">
                  <h1>Không tìm thấy trang</h1>
                  <a href="/" onClick={(e) => navigate(e, "/")}>
                    Trở về tìm kiếm
                  </a>
                </section>
              )}
            </Suspense>
          </main>
        </div>
      </CurrentAccountContext.Provider>
    </FavoritesProvider>
  );
}
