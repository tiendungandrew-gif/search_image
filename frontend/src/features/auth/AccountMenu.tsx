import { Avatar } from "../../components/Avatar";
import { useEffect, useRef } from "react";
import type { MouseEvent } from "react";
import type { Account } from "../../types/access";

export function AccountMenu({
  user,
  onNavigate,
  onLogout,
}: {
  user: Account;
  onNavigate: (event: MouseEvent<HTMLAnchorElement>, path: string) => void;
  onLogout: () => void;
}) {
  const menu = useRef<HTMLDetailsElement>(null);
  const toggle = useRef<HTMLElement>(null);
  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !menu.current?.contains(event.target)
      ) {
        if (menu.current) menu.current.open = false;
      }
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && menu.current?.open) {
        menu.current.open = false;
        toggle.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, []);
  return (
    <details ref={menu} className="profile-dropdown">
      <summary
        ref={toggle}
        aria-label={`Menu tài khoản của ${user.display_name}`}
      >
        <Avatar name={user.display_name} url={user.avatar_url} />
        <span className="profile-name">{user.display_name}</span>
        <svg
          className="profile-chevron"
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        >
          <path d="m7 10 5 5 5-5" />
        </svg>
      </summary>
      <div className="profile-panel">
        <strong>{user.display_name}</strong>
        <span className="profile-username">@{user.username}</span>

        <span className="profile-role">
          {user.role === "admin" ? "Quản trị viên" : "Thành viên"}
          {user.is_demo ? " · Trải nghiệm" : ""}
        </span>
        <a
          href="/profile"
          onClick={(event) => {
            if (menu.current) menu.current.open = false;
            onNavigate(event, "/profile");
          }}
        >
          Hồ sơ của tôi
        </a>
        <a
          href="/favorites"
          onClick={(event) => {
            if (menu.current) menu.current.open = false;
            onNavigate(event, "/favorites");
          }}
        >
          Ảnh yêu thích
        </a>
        {!user.is_demo && (
          <a
            href="/account"
            onClick={(event) => {
              if (menu.current) menu.current.open = false;
              onNavigate(event, "/account");
            }}
          >
            Đổi mật khẩu
          </a>
        )}
        <button type="button" onClick={onLogout}>
          Đăng xuất
        </button>
      </div>
    </details>
  );
}
