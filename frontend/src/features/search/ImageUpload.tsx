import { validateImage } from "./validation";
import { useEffect, useState } from "react";
import { Icon } from "../../components/Icon";

export function ImageUpload({
  file,
  onChange,
  maxBytes = 20 * 1024 ** 2,
  disabled = false,
}: {
  disabled?: boolean;
  file: File | null;
  onChange: (file: File | null) => void;
  maxBytes?: number;
}) {
  const [preview, setPreview] = useState<{ file: File; url: string } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    // The URL is an external browser resource, owned and revoked by this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPreview({ file, url });
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function choose(files: File[]) {
    if (disabled) return;
    if (files.length !== 1) {
      setError("Chọn đúng một ảnh tham chiếu.");
      return;
    }
    const issue = validateImage(files[0], maxBytes);
    setError(issue);
    if (!issue) onChange(files[0]);
  }
  return (
    <div>
      <label
        className={`upload-area ${dragging ? "is-dragging" : ""}`}
        htmlFor="reference-image"
        aria-disabled={disabled}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          choose(Array.from(event.dataTransfer.files));
        }}
      >
        {file && preview?.file === file ? (
          <img
            src={preview.url}
            alt="Ảnh tham chiếu xem trước"
            onError={() => {
              setError("Không đọc được ảnh đã chọn.");
              onChange(null);
            }}
          />
        ) : (
          <span className="upload-icon">
            <Icon kind="image" />
          </span>
        )}
        <span>
          <strong>{file ? file.name : "Thêm ảnh tham chiếu"}</strong>
          <small>
            {file
              ? `${(file.size / 1024).toFixed(1)} KiB · Chỉ dùng để tìm ảnh tương tự.`
              : `Kéo thả hoặc chọn · JPEG, PNG, WebP · Tối đa ${(maxBytes / 1024 ** 2).toFixed(0)} MiB`}
          </small>
        </span>
        <span className="upload-action">{file ? "Đổi ảnh" : "Chọn ảnh"} ↗</span>
        <input
          id="reference-image"
          aria-label="Thêm ảnh tham chiếu"
          type="file"
          disabled={disabled}
          aria-describedby={error ? "reference-image-error" : undefined}
          aria-invalid={Boolean(error)}
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => {
            if (event.target.files?.length)
              choose(Array.from(event.target.files));
            event.target.value = "";
          }}
        />
      </label>
      {file && (
        <button
          className="text-button"
          type="button"
          disabled={disabled}
          onClick={() => {
            onChange(null);
            setError(null);
          }}
        >
          Bỏ ảnh tham chiếu
        </button>
      )}
      {error && (
        <p id="reference-image-error" role="alert" className="error-message">
          {error}
        </p>
      )}
    </div>
  );
}
