import type { AdvancedSettings } from "./validation";
import type { MetadataFilters } from "../../types/api";
import { useState } from "react";
import type { DatasetReference } from "../../types/access";

export function AdvancedControls({
  value,
  onChange,
  fusionAvailable,
  rerankAvailable,
  disabled,
  datasets,
  simple = false,
}: {
  simple?: boolean;
  value: AdvancedSettings;
  onChange: (value: AdvancedSettings) => void;
  fusionAvailable: boolean;
  rerankAvailable: boolean;
  disabled: boolean;
  datasets?: DatasetReference[];
}) {
  const [tags, setTags] = useState(value.filters.tags_any?.join(", ") ?? "");
  function filter(
    key: keyof MetadataFilters,
    item: string | number | string[] | undefined,
  ) {
    onChange({ ...value, filters: { ...value.filters, [key]: item } });
  }
  return (
    <details className="advanced-controls">
      <summary>
        {simple ? "Thư viện và bộ lọc" : "Tùy chọn tìm kiếm nâng cao"}
      </summary>
      <fieldset disabled={disabled}>
        <legend>
          {simple ? "Giới hạn ảnh bạn muốn tìm" : "Bộ lọc metadata"}
        </legend>
        <p className="muted">
          {simple
            ? "Chọn thông tin đã được lưu cho ảnh. Bạn có thể để trống để tìm trong tất cả thư viện được chia sẻ."
            : "Các bộ lọc được kết hợp bằng AND và áp dụng trên backend."}
        </p>
        <div className="filter-grid">
          <label htmlFor="filter-source">
            Thư viện ảnh
            {datasets ? (
              <select
                id="filter-source"
                value={value.filters.source_dataset ?? ""}
                onChange={(event) =>
                  filter("source_dataset", event.target.value || undefined)
                }
              >
                <option value="">Tất cả thư viện được cấp quyền</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.key}>
                    {d.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id="filter-source"
                maxLength={128}
                value={value.filters.source_dataset ?? ""}
                onChange={(event) =>
                  filter("source_dataset", event.target.value || undefined)
                }
                placeholder="Tên dataset đã nhập"
              />
            )}
          </label>
          <label htmlFor="filter-city">
            Thành phố
            <input
              id="filter-city"
              maxLength={128}
              value={value.filters.city ?? ""}
              onChange={(event) =>
                filter("city", event.target.value || undefined)
              }
            />
          </label>
          <label htmlFor="filter-tags-any">
            {simple
              ? "Thẻ ảnh (cách nhau bằng dấu phẩy)"
              : "Có ít nhất một tag"}
            <input
              id="filter-tags-any"
              value={tags}
              onChange={(event) => {
                setTags(event.target.value);
                filter(
                  "tags_any",
                  event.target.value
                    .split(",")
                    .map((tag) => tag.normalize("NFC").trim().toLowerCase())
                    .filter(Boolean),
                );
              }}
              placeholder="coffee, outdoor"
            />
          </label>
          <label htmlFor="filter-format">
            Định dạng
            <select
              id="filter-format"
              value={value.filters.media_types?.[0] ?? ""}
              onChange={(event) =>
                filter(
                  "media_types",
                  event.target.value ? [event.target.value] : undefined,
                )
              }
            >
              <option value="">Tất cả</option>
              <option value="image/jpeg">JPEG</option>
              <option value="image/png">PNG</option>
              <option value="image/webp">WebP</option>
            </select>
          </label>
          {(
            [
              ["min_width", "Chiều rộng tối thiểu"],
              ["max_width", "Chiều rộng tối đa"],
              ["min_height", "Chiều cao tối thiểu"],
              ["max_height", "Chiều cao tối đa"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} htmlFor={`filter-${key}`}>
              {label}
              <input
                id={`filter-${key}`}
                type="number"
                min={1}
                step={1}
                value={value.filters[key] ?? ""}
                onChange={(event) =>
                  filter(
                    key,
                    event.target.value ? Number(event.target.value) : undefined,
                  )
                }
              />
            </label>
          ))}
        </div>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setTags("");
            onChange({ ...value, filters: {} });
          }}
        >
          Xóa bộ lọc
        </button>
      </fieldset>
      {!simple && (
        <fieldset disabled={!fusionAvailable}>
          <legend>Kết hợp văn bản và ảnh</legend>
          <label className="field-label" htmlFor="fusion-strategy">
            Kết hợp kết quả
          </label>
          <select
            id="fusion-strategy"
            value={value.fusion}
            onChange={(event) =>
              onChange({
                ...value,
                fusion: event.target.value as AdvancedSettings["fusion"],
              })
            }
          >
            <option value="rrf">RRF · theo thứ hạng</option>
            <option value="weighted_rrf">
              Weighted RRF · thứ hạng có trọng số
            </option>
            <option value="weighted_score">
              Weighted score · cosine đã đổi thang
            </option>
          </select>
          <label className="field-label" htmlFor="text-weight">
            Trọng số văn bản {value.textWeight.toFixed(2)} · ảnh{" "}
            {(1 - value.textWeight).toFixed(2)}
          </label>
          <input
            id="text-weight"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={value.textWeight}
            onChange={(event) =>
              onChange({ ...value, textWeight: Number(event.target.value) })
            }
          />
        </fieldset>
      )}
      <label className="rerank-control">
        <input
          type="checkbox"
          disabled={!rerankAvailable}
          checked={value.rerank && rerankAvailable}
          onChange={(event) =>
            onChange({ ...value, rerank: event.target.checked })
          }
        />{" "}
        {simple
          ? "Ưu tiên ảnh đáp ứng đủ yêu cầu"
          : "Xếp hạng lại theo điều kiện"}
      </label>
      <p className="muted">
        {simple ? (
          disabled ? (
            "Cách tìm hiện tại không dùng các bộ lọc này."
          ) : (
            "Bạn có thể bỏ bớt bộ lọc nếu chưa tìm thấy ảnh phù hợp."
          )
        ) : (
          <>
            Điều kiện thị giác chưa có bằng chứng được ghi là “Chưa xác minh”.{" "}
            {disabled ? "Agent chưa hỗ trợ các bộ lọc này." : ""}
          </>
        )}
      </p>
    </details>
  );
}
