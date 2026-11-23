import { useEffect, useRef } from "react";

export function DiscoveryMore({
  hasMore,
  loading,
  error,
  onLoad,
}: {
  hasMore: boolean;
  loading: boolean;
  error: string | null;
  onLoad: () => void;
}) {
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (
      !hasMore ||
      loading ||
      error ||
      !sentinel.current ||
      typeof IntersectionObserver === "undefined"
    )
      return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) onLoad();
      },
      { rootMargin: "600px" },
    );
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [hasMore, loading, error, onLoad]);
  return (
    <div ref={sentinel} className="discovery-more">
      {loading ? (
        <p role="status">Đang tải thêm ảnh…</p>
      ) : error ? (
        <>
          <p role="status">Chưa tải được ảnh tiếp theo. {error}</p>
          <button type="button" className="secondary-button" onClick={onLoad}>
            Thử tải thêm
          </button>
        </>
      ) : hasMore ? (
        <button type="button" className="secondary-button" onClick={onLoad}>
          Xem thêm ảnh
        </button>
      ) : (
        <p role="status">Bạn đã xem hết ảnh trong thư viện hiện tại.</p>
      )}
    </div>
  );
}
