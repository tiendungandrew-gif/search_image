import type { AdvancedSearchInput, MetadataFilters } from "../../types/api";

export interface AdvancedSettings {
  fusion: NonNullable<AdvancedSearchInput["fusion"]>["method"];
  textWeight: number;
  rerank: boolean;
  filters: MetadataFilters;
}
export const defaultAdvanced: AdvancedSettings = {
  fusion: "rrf",
  textWeight: 0.5,
  rerank: false,
  filters: {},
};
export function filterError(filters: MetadataFilters) {
  for (const [min, max] of [
    [filters.min_width, filters.max_width],
    [filters.min_height, filters.max_height],
  ])
    if (min && max && min > max)
      return "Kích thước tối thiểu phải nhỏ hơn hoặc bằng tối đa.";
  for (const tags of [filters.tags_any, filters.tags_all])
    if (tags && (tags.length > 20 || tags.some((tag) => tag.length > 64)))
      return "Mỗi bộ lọc có tối đa 20 tag, mỗi tag tối đa 64 ký tự.";
  return null;
}

export function validateImage(
  file: File,
  limit = 20 * 1024 ** 2,
): string | null {
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
    return "Chọn ảnh JPEG, PNG hoặc WebP.";
  if (file.size === 0) return "File ảnh rỗng.";
  if (file.size > limit)
    return `Ảnh vượt giới hạn ${(limit / 1024 ** 2).toFixed(0)} MiB.`;
  return null;
}
