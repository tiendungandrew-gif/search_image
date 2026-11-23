import { useEffect, useState } from "react";
import { useFavorites } from "./FavoritesContext";
export function FavoriteButton({
  imageId,
  compact = false,
}: {
  imageId: string;
  compact?: boolean;
}) {
  const { saved, pending, ensure, toggle } = useFavorites();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => ensure(imageId), [imageId, ensure]);
  const active = saved[imageId] ?? false;
  return (
    <div className={`favorite-control${compact ? " is-compact" : ""}`}>
      <button
        type="button"
        className={`favorite-button${active ? " is-saved" : ""}`}
        aria-label={active ? "Bỏ yêu thích ảnh" : "Yêu thích ảnh"}
        aria-pressed={active}
        title={active ? "Bỏ yêu thích" : "Lưu vào ảnh yêu thích"}
        disabled={pending.has(imageId)}
        onClick={async () => {
          setError(null);
          try {
            await toggle(imageId);
          } catch (error) {
            setError(
              error instanceof Error ? error.message : "Chưa lưu được ảnh.",
            );
          }
        }}
      >
        <svg
          width="21"
          height="21"
          viewBox="0 0 24 24"
          fill={active ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />
        </svg>
        {!compact && <span>{active ? "Đã yêu thích" : "Yêu thích"}</span>}
      </button>
      {error && (
        <span className="favorite-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
