import { useEffect, useRef, useState } from "react";
import { apiMediaURL } from "../../services/api/media";
import { accessHeaders } from "../../services/api/security";

/** Defer the authenticated network request itself, not only the image decode. */
export function ResultImage({
  url,
  token,
  alt,
  eager = false,
  onOpen,
  actionLabel,
}: {
  url: string;
  token: string;
  alt: string;
  eager?: boolean;
  onOpen?: () => void;
  actionLabel?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(eager);
  const [attempt, setAttempt] = useState(0);
  const [resource, setResource] = useState<{
    key: string;
    src: string;
    fetchedMs: number;
  } | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [decoded, setDecoded] = useState<number | null>(null);
  const started = useRef(0);
  const key = `${url}|${token}|${attempt}`;
  useEffect(() => {
    if (eager || !globalThis.IntersectionObserver) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "160px" },
    );
    if (host.current) observer.observe(host.current);
    return () => observer.disconnect();
  }, [eager]);
  useEffect(() => {
    if (!visible && !eager && globalThis.IntersectionObserver) return;
    const controller = new AbortController();
    let blobURL: string | null = null;
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 8000);
    started.current = performance.now();
    async function load() {
      setFailure(null);
      setDecoded(null);
      try {
        const response = await fetch(apiMediaURL(url), {
          headers: accessHeaders(token),
          credentials: "same-origin",
          signal: controller.signal,
        });
        if (!response.ok)
          throw new Error(
            response.status === 401 || response.status === 403
              ? "Phiên truy cập ảnh đã hết hiệu lực."
              : `Không tải được ảnh (HTTP ${response.status}).`,
          );
        const type = response.headers.get("content-type")?.split(";")[0];
        if (!["image/jpeg", "image/png", "image/webp"].includes(type ?? ""))
          throw new Error("Nội dung ảnh không hợp lệ.");
        const blob = await response.blob();
        if (blob.size > 20 * 1024 ** 2)
          throw new Error("Ảnh vượt giới hạn hiển thị.");
        if (controller.signal.aborted) return;
        blobURL = URL.createObjectURL(blob);
        setResource({
          key,
          src: blobURL,
          fetchedMs: performance.now() - started.current,
        });
      } catch (error) {
        if (!controller.signal.aborted || timedOut)
          setFailure(
            timedOut
              ? "Tải ảnh quá thời gian chờ."
              : error instanceof Error
                ? error.message
                : "Không tải được ảnh.",
          );
      } finally {
        clearTimeout(timer);
      }
    }
    void load();
    return () => {
      controller.abort();
      clearTimeout(timer);
      if (blobURL) URL.revokeObjectURL(blobURL);
    };
  }, [url, token, key, visible, eager]);
  const current = resource?.key === key ? resource : null;
  const media = (
    <img
      src={current?.src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      hidden={!current}
      onLoad={() => setDecoded(performance.now() - started.current)}
      onError={() => setFailure("Không đọc được ảnh.")}
    />
  );
  return (
    <div
      className={`result-media ${eager ? "full-media" : ""}`}
      ref={host}
      data-ready={current && decoded !== null ? "true" : "false"}
      data-fetch-ms={current?.fetchedMs.toFixed(2)}
      data-image-ms={decoded?.toFixed(2)}
    >
      {failure ? (
        <div className="image-placeholder">
          <span>{failure}</span>
          <button
            type="button"
            onClick={() => {
              setFailure(null);
              setAttempt((n) => n + 1);
            }}
          >
            Thử tải lại ảnh
          </button>
        </div>
      ) : (
        <>
          {onOpen && current ? (
            <button
              type="button"
              className="gallery-preview-action"
              onClick={onOpen}
              aria-label={actionLabel ?? `Phóng to ${alt}`}
            >
              {media}
              <span className="preview-action-label" aria-hidden="true">
                Xem ảnh ↗
              </span>
            </button>
          ) : (
            media
          )}
          {!current && (
            <div
              className="image-placeholder"
              role="img"
              aria-label={`Đang tải ${alt}`}
            >
              <span className="image-shimmer" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
