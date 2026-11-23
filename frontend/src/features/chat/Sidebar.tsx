import { useEffect, useRef, useState } from "react";
import type { MouseEvent } from "react";
import type { Account, DatasetReference } from "../../types/access";
import { Avatar } from "../../components/Avatar";
import ChatWidget from "./ChatWidget";
import { RailIcon } from "./RailIcon";

export function Sidebar({
  user,
  path,
  datasets,
  onNavigate,
}: {
  user: Account | null;
  path: string;
  datasets: DatasetReference[];
  onNavigate: (event: MouseEvent<HTMLAnchorElement>, path: string) => void;
}) {
  const [librariesOpen, setLibrariesOpen] = useState(false);
  const library = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!librariesOpen) return;
    const dismiss = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !library.current?.contains(event.target)
      )
        setLibrariesOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setLibrariesOpen(false);
        toggle.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [librariesOpen]);
  return (
    <nav className="side-rail" aria-label="Điều hướng chính">
      <a
        className="rail-logo"
        href="/"
        aria-label="Synlens trang chủ"
        title="Synlens"
      >
        <img src="/branding/synlens-logo.png" alt="" />
      </a>
      <a
        className="rail-action"
        href="/"
        aria-label="Trang chủ"
        title="Trang chủ"
        aria-current={path === "/" ? "page" : undefined}
        onClick={(event) => onNavigate(event, "/")}
      >
        <RailIcon kind="home" active={path === "/"} />
      </a>
      {/* Temporarily hidden until these sidebar actions are needed. */}
      <div hidden>
        <div ref={library} className="rail-library">
          <button
            ref={toggle}
            className="rail-action"
            type="button"
            aria-label="Thư viện ảnh"
            title="Thư viện ảnh"
            aria-expanded={librariesOpen}
            aria-controls="rail-library-panel"
            onClick={() => setLibrariesOpen((value) => !value)}
          >
            <RailIcon kind="library" />
          </button>
          {librariesOpen && (
            <aside
              className="rail-library-panel"
              id="rail-library-panel"
              aria-label="Thư viện ảnh"
            >
              <div className="chat-panel-heading">
                <strong>
                  {user ? "Thư viện của bạn" : "Thư viện công khai"}
                </strong>
                <button
                  className="rail-close"
                  type="button"
                  aria-label="Đóng thư viện"
                  onClick={() => {
                    setLibrariesOpen(false);
                    toggle.current?.focus();
                  }}
                >
                  ✕
                </button>
              </div>
              <div className="rail-library-list">
                {datasets.length ? (
                  datasets.map((dataset) => (
                    <div className="rail-library-card" key={dataset.id}>
                      <RailIcon kind="library" />
                      <div>
                        <strong>{dataset.name}</strong>
                        <small>
                          {dataset.is_public
                            ? "Công khai"
                            : "Bạn được quyền truy cập"}
                        </small>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="chat-empty">Chưa có thư viện ảnh khả dụng.</p>
                )}
              </div>
            </aside>
          )}
        </div>
        <a
          className="rail-action"
          href="/"
          aria-label="Tìm kiếm bằng ảnh"
          title="Tìm kiếm bằng ảnh"
          onClick={(event) => {
            if (
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            setLibrariesOpen(false);
            const openUpload = () => {
              const button = document.querySelector<HTMLButtonElement>(
                'button[aria-label="Tìm bằng ảnh"]',
              );
              if (!button) return false;
              button.click();
              return true;
            };
            if (path === "/") {
              event.preventDefault();
              openUpload();
              return;
            }
            if (
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            onNavigate(event, "/");
            const observer = new MutationObserver(() => {
              if (openUpload()) {
                observer.disconnect();
                clearTimeout(timer);
              }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            const timer = setTimeout(() => observer.disconnect(), 5000);
          }}
        >
          <RailIcon kind="plus" />
        </a>
      </div>
      <a
        className="rail-action"
        href="/favorites"
        aria-label="Ảnh yêu thích"
        title="Ảnh yêu thích"
        aria-current={path === "/favorites" ? "page" : undefined}
        onClick={(event) => onNavigate(event, "/favorites")}
      >
        <RailIcon kind="heart" active={path === "/favorites"} />
      </a>
      <ChatWidget key={user?.id ?? "guest"} user={user} rail />
      {user && (
        <a
          className="rail-action rail-profile"
          href="/profile"
          aria-label="Hồ sơ cá nhân"
          title="Hồ sơ cá nhân"
          aria-current={path === "/profile" ? "page" : undefined}
          onClick={(event) => onNavigate(event, "/profile")}
        >
          <Avatar name={user.display_name} url={user.avatar_url} />
        </a>
      )}
      {user?.role === "admin" && (
        <a
          className="rail-action rail-admin"
          href="/admin"
          aria-label="Quản trị"
          title="Quản trị"
          aria-current={path.startsWith("/admin") ? "page" : undefined}
          onClick={(event) => onNavigate(event, "/admin")}
        >
          <RailIcon kind="admin" active={path.startsWith("/admin")} />
        </a>
      )}
    </nav>
  );
}
