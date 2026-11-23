import { Icon } from "../../components/Icon";
import { flushSync } from "react-dom";

export function DiscoveryHero() {
  return (
    <div className="discovery-art" aria-hidden="true">
      <div className="discovery-orbit" />
      <div className="discovery-art-card art-landscape">
        <Icon kind="image" />
        <span>Thiên nhiên</span>
      </div>
      <div className="discovery-art-card art-architecture">
        <Icon kind="hotel" />
        <span>Kiến trúc</span>
      </div>
      <div className="discovery-art-card art-ideas">
        <Icon kind="search" />
        <span>Mọi ý tưởng</span>
      </div>
    </div>
  );
}

export function GalleryView({
  compact,
  onChange,
}: {
  compact: boolean;
  onChange: (value: boolean) => void;
}) {
  const changeView = (value: boolean) => {
    if (value === compact) return;
    if (
      !document.startViewTransition ||
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    ) {
      onChange(value);
      return;
    }
    try {
      const transition = document.startViewTransition(() => {
        flushSync(() => onChange(value));
      });
      void transition.ready.catch(() => undefined);
      void transition.finished.catch(() => undefined);
    } catch {
      onChange(value);
    }
  };
  return (
    <div className="gallery-view" role="group" aria-label="Cách hiển thị ảnh">
      <button
        type="button"
        aria-label="Lưới lớn"
        aria-pressed={!compact}
        onClick={() => changeView(false)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="Lưới gọn"
        aria-pressed={compact}
        onClick={() => changeView(true)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <path d="M3 3h4v4H3zm7 0h4v4h-4zm7 0h4v4h-4zM3 10h4v4H3zm7 0h4v4h-4zm7 0h4v4h-4zM3 17h4v4H3zm7 0h4v4h-4zm7 0h4v4h-4z" />
        </svg>
      </button>
    </div>
  );
}
