import { FavoriteButton } from "../profile/FavoriteButton";
import { lazy, Suspense, useLayoutEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { ImageMetadata, SearchResult } from "../../types/api";
import { ResultImage } from "./ResultImage";

const ImageDetailDialog = lazy(() => import("./ImageDetailDialog"));
export interface GalleryImage {
  image_id: string;
  rank: number;
  score: number | null;
  score_type: string | null;
  image_url: string;
  thumbnail_url: string;
  metadata: ImageMetadata;
  constraint_assessments?: SearchResult["constraint_assessments"];
}
export function ConstraintEvidence({
  assessments,
  showDiagnostics = true,
}: {
  assessments: NonNullable<GalleryImage["constraint_assessments"]>;
  showDiagnostics?: boolean;
}) {
  return (
    assessments.length > 0 && (
      <ul className="constraint-evidence">
        {assessments.map((item, index) => (
          <li key={item.clause_id}>
            {showDiagnostics ? item.clause_id : `Yêu cầu ${index + 1}`}:{" "}
            {item.status === "satisfied"
              ? "Metadata khớp"
              : item.status === "violated"
                ? "Metadata không khớp"
                : "Chưa xác minh"}
            {showDiagnostics && item.semantic_score != null
              ? ` · cosine ${item.semantic_score.toFixed(3)}`
              : ""}
            {showDiagnostics && item.evidence_ref && (
              <small>Bằng chứng: {item.evidence_ref}</small>
            )}
          </li>
        ))}
      </ul>
    )
  );
}
export function ResultGallery({
  images,
  token,
  onVisible,
  showDiagnostics = true,
  datasetNames = {},
  showRanks = true,
}: {
  showRanks?: boolean;
  showDiagnostics?: boolean;
  datasetNames?: Record<string, string>;
  images: GalleryImage[];
  token: string;
  onVisible?: () => void;
}) {
  const grid = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const host = grid.current;
    if (showRanks || !host || typeof ResizeObserver === "undefined") return;
    let frame = 0;
    const layout = () => {
      const styles = getComputedStyle(host);
      const maxColumns =
        Number(styles.getPropertyValue("--discovery-columns")) || 4;
      const gap = parseFloat(styles.getPropertyValue("--discovery-gap")) || 22;
      const minWidth =
        parseFloat(styles.getPropertyValue("--discovery-min-width")) || 0;
      const columns =
        minWidth > 0
          ? Math.max(
              1,
              Math.min(
                maxColumns,
                Math.floor((host.clientWidth + gap) / (minWidth + gap)),
              ),
            )
          : maxColumns;
      const width = (host.clientWidth - gap * (columns - 1)) / columns;
      if (width <= 0) return;
      const heights = Array<number>(columns).fill(0);
      for (const card of host.children) {
        if (!(card instanceof HTMLElement)) continue;
        card.style.width = `${width}px`;
        const column = heights.indexOf(Math.min(...heights));
        card.style.position = "absolute";
        card.style.left = `${column * (width + gap)}px`;
        card.style.top = `${heights[column]}px`;
        heights[column] += card.getBoundingClientRect().height + gap;
      }
      host.style.height = `${Math.max(...heights, 0)}px`;
    };
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(layout);
    });
    observer.observe(host);
    for (const card of host.children) observer.observe(card);
    layout();
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [images.length, showRanks]);
  const [selected, setSelected] = useState<number | null>(null);
  useLayoutEffect(() => {
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => onVisible?.());
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, [onVisible]);
  return (
    <>
      {showDiagnostics && (
        <p className="gallery-note">
          Theo thứ hạng từ backend · Điểm xếp hạng không phải xác suất.
        </p>
      )}
      <div
        ref={grid}
        className={`result-grid${!showRanks ? " discovery-masonry" : ""}`}
      >
        {images.map((image, index) => (
          <article
            className="result-card"
            key={image.image_id}
            id={`image-${image.image_id}`}
            tabIndex={-1}
            style={
              {
                "--reveal-delay": `${Math.min(index, 7) * 32}ms`,
              } as CSSProperties
            }
          >
            <div
              className="card-image-wrap"
              style={
                !showDiagnostics
                  ? {
                      aspectRatio: Math.max(
                        0.65,
                        Math.min(
                          1.8,
                          image.metadata.width / image.metadata.height || 1,
                        ),
                      ),
                    }
                  : undefined
              }
            >
              <ResultImage
                url={image.thumbnail_url}
                token={token}
                onOpen={showDiagnostics ? undefined : () => setSelected(index)}
                actionLabel={`Phóng to ảnh hạng ${image.rank}`}
                alt={
                  (!showDiagnostics && image.metadata.caption) ||
                  image.metadata.title ||
                  (showDiagnostics
                    ? `Ảnh ${image.image_id.slice(0, 8)}`
                    : "Ảnh trong thư viện")
                }
              />
              {!showDiagnostics && (
                <FavoriteButton imageId={image.image_id} compact />
              )}
              {showRanks && <span className="rank-badge">#{image.rank}</span>}
            </div>
            <div className="result-description">
              <h3>
                <button
                  type="button"
                  className="detail-trigger"
                  onClick={() => setSelected(index)}
                  aria-label={`Xem chi tiết ảnh hạng ${image.rank}`}
                >
                  {(!showDiagnostics && image.metadata.caption) ||
                    image.metadata.title ||
                    (showDiagnostics
                      ? `Ảnh ${image.image_id.slice(0, 8)}`
                      : "Ảnh trong thư viện")}{" "}
                  <span aria-hidden="true">↗</span>
                </button>
              </h3>
              {showDiagnostics && (
                <p>{image.metadata.caption || "Chưa có chú thích"}</p>
              )}
              <div className="card-metrics">
                {showDiagnostics && (
                  <span>
                    {image.score === null
                      ? "Không có điểm ngữ nghĩa"
                      : `${image.score_type ?? "Điểm"} ${image.score.toFixed(image.score_type === "rrf" ? 5 : 3)}`}
                  </span>
                )}
                <small>
                  {image.metadata.width} × {image.metadata.height}
                </small>
              </div>
              {showDiagnostics && (
                <small>
                  {datasetNames[
                    image.metadata.source_dataset ?? "__unassigned__"
                  ] ??
                    image.metadata.source_dataset ??
                    "Chưa phân loại"}
                </small>
              )}
              {showDiagnostics && image.metadata.tags.length > 0 && (
                <div className="tag-list">
                  {image.metadata.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              )}
              <ConstraintEvidence
                assessments={image.constraint_assessments ?? []}
                showDiagnostics={showDiagnostics}
              />
            </div>
          </article>
        ))}
      </div>
      {selected !== null && images[selected] && (
        <Suspense fallback={<p role="status">Đang mở chi tiết ảnh…</p>}>
          <ImageDetailDialog
            images={images}
            selected={selected}
            token={token}
            showDiagnostics={showDiagnostics}
            datasetNames={datasetNames}
            onSelect={setSelected}
            onClose={() => setSelected(null)}
          />
        </Suspense>
      )}
    </>
  );
}
