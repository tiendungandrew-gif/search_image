import type { ImageMetadata } from "../../types/api";

import { displayMetadata } from "./metadataDisplay";

export function ImageMetadataSummary({
  metadata,
  imageId,
}: {
  metadata: ImageMetadata;
  imageId: string;
}) {
  const city = displayMetadata(metadata.city);
  const license = displayMetadata(metadata.license);
  const format =
    (
      {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WebP",
      } as Record<string, string>
    )[metadata.media_type] ?? metadata.media_type;
  return (
    <div className="image-metadata-summary">
      {(city || license) && (
        <dl className="image-context">
          {city && (
            <div>
              <dt>Địa điểm</dt>
              <dd>{city}</dd>
            </div>
          )}
          {license && (
            <div>
              <dt>Giấy phép</dt>
              <dd>{license}</dd>
            </div>
          )}
        </dl>
      )}
      <details className="image-technical-details" key={imageId}>
        <summary>Thông tin ảnh</summary>
        <dl>
          <div>
            <dt>Kích thước</dt>
            <dd>
              {metadata.width} × {metadata.height} px
            </dd>
          </div>
          <div>
            <dt>Định dạng</dt>
            <dd>{format}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}
