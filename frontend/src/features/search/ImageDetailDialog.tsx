import { ImageComments } from "./ImageComments";
import { FavoriteButton } from "../profile/FavoriteButton";
import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api/client";
import type { ImageDetail } from "../../types/api";
import { ConstraintEvidence, type GalleryImage } from "./ResultGallery";
import { ImageMetadataSummary } from "./ImageMetadataSummary";
import { displayMetadata } from "./metadataDisplay";
import { RelatedImages } from "./RelatedImages";
import { ResultImage } from "./ResultImage";

export default function ImageDetailDialog({
  images,
  selected,
  token,
  onSelect,
  onClose,
  showDiagnostics = true,
  datasetNames = {},
}: {
  showDiagnostics?: boolean;
  datasetNames?: Record<string, string>;
  images: GalleryImage[];
  selected: number;
  token: string;
  onSelect: (index: number) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [detail, setDetail] = useState<ImageDetail | null>(null);
  const [error, setError] = useState<{ id: string; message: string } | null>(
    null,
  );
  const [attempt, setAttempt] = useState(0);
  const [closing, setClosing] = useState(false);
  const close = () => {
    if (
      !dialog.current?.closest(".consumer-site") ||
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    )
      onClose();
    else setClosing(true);
  };
  useEffect(() => {
    if (!closing) return;
    const timer = window.setTimeout(onClose, 170);
    return () => window.clearTimeout(timer);
  }, [closing, onClose]);
  const parentImage = images[selected];
  const [relatedSelection, setRelatedSelection] = useState<{
    parentId: string;
    image: GalleryImage;
  } | null>(null);
  const image =
    relatedSelection?.parentId === parentImage.image_id
      ? relatedSelection.image
      : parentImage;
  useEffect(() => {
    dialog.current?.scrollTo?.({ top: 0 });
  }, [image.image_id]);
  const previous = () => {
    if (!closing) {
      setRelatedSelection(null);
      onSelect((selected - 1 + images.length) % images.length);
    }
  };
  const next = () => {
    if (!closing) {
      setRelatedSelection(null);
      onSelect((selected + 1) % images.length);
    }
  };
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      opener?.focus();
    };
  }, []);
  useEffect(() => {
    const request = new AbortController();
    void api
      .imageDetail(image.image_id, token, request.signal)
      .then((value) => {
        if (!request.signal.aborted) setDetail(value);
      })
      .catch((issue) => {
        if (!request.signal.aborted)
          setError({
            id: image.image_id,
            message:
              issue instanceof Error
                ? issue.message
                : "Không tải được metadata.",
          });
      });
    return () => request.abort();
  }, [image.image_id, token, attempt]);
  const currentError = error?.id === image.image_id ? error.message : null;
  const current = detail?.image_id === image.image_id ? detail : null;
  const meta = current?.metadata ?? image.metadata;
  return (
    <dialog
      className={`image-dialog${closing ? " is-closing" : ""}`}
      ref={dialog}
      aria-labelledby="detail-title"
      aria-describedby="detail-position"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          previous();
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          next();
        }
      }}
    >
      <div className="dialog-toolbar">
        <p id="detail-position" role="status">
          {relatedSelection?.parentId === parentImage.image_id
            ? "Đang xem ảnh cùng chủ đề"
            : `Ảnh ${selected + 1} / ${images.length}`}
          {showDiagnostics ? ` · Hạng ${image.rank}` : ""}
        </p>
        <div>
          <button
            type="button"
            onClick={previous}
            disabled={closing}
            aria-label="Ảnh trước"
            title="Ảnh trước (←)"
          >
            ←
          </button>
          <button
            type="button"
            onClick={next}
            disabled={closing}
            aria-label="Ảnh tiếp theo"
            title="Ảnh tiếp theo (→)"
          >
            →
          </button>
          <button
            type="button"
            autoFocus
            onClick={close}
            aria-label="Đóng chi tiết ảnh"
            title="Đóng (Esc)"
          >
            Đóng ✕
          </button>
        </div>
      </div>
      <div className="dialog-body">
        <div className="detail-image" key={image.image_id}>
          <ResultImage
            key={image.image_id}
            eager
            url={image.image_url}
            token={token}
            alt={meta.title ?? "Ảnh gốc"}
          />
        </div>
        <section className="detail-metadata">
          {!showDiagnostics && <FavoriteButton imageId={image.image_id} />}
          <h2 id="detail-title">{meta.title || "Chi tiết ảnh"}</h2>
          {!current && !currentError && (
            <p role="status">Đang tải thông tin ảnh…</p>
          )}
          {currentError && (
            <div role="alert">
              <p>{currentError}</p>
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setAttempt((n) => n + 1);
                }}
              >
                Tải lại thông tin
              </button>
              <p>Thông tin bên dưới lấy từ kết quả tìm kiếm.</p>
            </div>
          )}
          {displayMetadata(meta.caption) && meta.caption !== meta.title && (
            <p className="image-caption">{meta.caption}</p>
          )}
          {!showDiagnostics ? (
            <ImageMetadataSummary metadata={meta} imageId={image.image_id} />
          ) : (
            <>
              <dl>
                {Object.entries({
                  ...(showDiagnostics ? { "Mã ảnh": image.image_id } : {}),
                  "Kích thước": `${meta.width} × ${meta.height}`,
                  "Định dạng": meta.media_type,
                  [showDiagnostics ? "Dataset" : "Thư viện"]:
                    datasetNames[meta.source_dataset ?? "__unassigned__"] ??
                    meta.source_dataset,
                  "Thành phố": meta.city,
                  "Giấy phép": meta.license,
                  ...(showDiagnostics
                    ? {
                        "Điểm xếp hạng":
                          image.score === null
                            ? null
                            : `${image.score_type} ${image.score.toFixed(5)}`,
                      }
                    : {}),
                  "Ngày thêm": current?.created_at
                    ? new Date(current.created_at).toLocaleDateString("vi-VN")
                    : null,
                }).map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value || "Chưa có thông tin"}</dd>
                  </div>
                ))}
              </dl>
              <div className="tag-list">
                {meta.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <ConstraintEvidence
                assessments={image.constraint_assessments ?? []}
                showDiagnostics={showDiagnostics}
              />
              <p className="muted">
                Ảnh được tải qua API có xác thực. Điểm truy xuất không xác nhận
                sự hiện diện của đối tượng trong ảnh.
              </p>
            </>
          )}
          {!showDiagnostics && (
            <ImageComments key={image.image_id} imageId={image.image_id} />
          )}
        </section>
      </div>
      {!showDiagnostics && (
        <RelatedImages
          key={image.image_id}
          imageId={image.image_id}
          token={token}
          onSelect={(selectedImage) => {
            setRelatedSelection({
              parentId: parentImage.image_id,
              image: selectedImage,
            });
          }}
        />
      )}
    </dialog>
  );
}
