import { FavoriteButton } from "../profile/FavoriteButton";
import { useEffect, useState } from "react";
import { api } from "../../services/api/client";
import type { GalleryImage } from "./ResultGallery";
import { ResultImage } from "./ResultImage";

export function RelatedImages({
  imageId,
  token,
  onSelect,
}: {
  imageId: string;
  token: string;
  onSelect: (image: GalleryImage) => void;
}) {
  const [attempt, setAttempt] = useState(0);
  const [snapshot, setSnapshot] = useState<{
    id: string;
    token: string;
    images: GalleryImage[];
    error: string | null;
  } | null>(null);
  useEffect(() => {
    const request = new AbortController();
    void api
      .relatedImages(imageId, token, request.signal)
      .then((response) => {
        if (!request.signal.aborted)
          setSnapshot({
            id: imageId,
            token,
            images: response.results.filter(
              (image) => image.image_id !== imageId,
            ),
            error: null,
          });
      })
      .catch((issue: unknown) => {
        if (!request.signal.aborted)
          setSnapshot({
            id: imageId,
            token,
            images: [],
            error:
              issue instanceof Error
                ? issue.message
                : "Chưa tải được ảnh cùng chủ đề.",
          });
      });
    return () => request.abort();
  }, [imageId, token, attempt]);
  const current =
    snapshot?.id === imageId && snapshot.token === token ? snapshot : null;
  return (
    <section className="related-images" aria-labelledby="related-heading">
      <h2 id="related-heading">Ảnh cùng chủ đề</h2>
      {!current ? (
        <p role="status">Đang tìm ảnh cùng chủ đề…</p>
      ) : current.error ? (
        <div role="status">
          <p>{current.error}</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setSnapshot(null);
              setAttempt((value) => value + 1);
            }}
          >
            Tải lại ảnh cùng chủ đề
          </button>
        </div>
      ) : current.images.length === 0 ? (
        <p>Chưa có ảnh liên quan trong thư viện bạn được xem.</p>
      ) : (
        <div className="related-grid">
          {current.images.map((image) => (
            <article key={image.image_id}>
              <div
                className="related-media"
                style={{
                  aspectRatio:
                    image.metadata.width / image.metadata.height || 1,
                }}
              >
                <FavoriteButton imageId={image.image_id} compact />
                <ResultImage
                  url={image.thumbnail_url}
                  token={token}
                  alt={
                    image.metadata.title ||
                    image.metadata.caption ||
                    "Ảnh cùng chủ đề"
                  }
                  actionLabel={`Xem ảnh liên quan: ${image.metadata.title || "Ảnh trong thư viện"}`}
                  onOpen={() => onSelect(image)}
                />
              </div>
              <button
                type="button"
                className="detail-trigger"
                onClick={() => onSelect(image)}
              >
                {image.metadata.title || image.metadata.caption || "Xem ảnh"}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
