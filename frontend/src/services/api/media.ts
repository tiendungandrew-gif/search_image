import { APIClientError } from "./client";

export function apiMediaURL(path: string) {
  if (
    !/^\/api\/v1\/images\/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}\/content\?variant=(original|thumbnail)$/.test(
      path,
    )
  )
    throw new APIClientError(
      "INVALID_MEDIA_URL",
      "Đường dẫn ảnh không hợp lệ.",
    );
  const base = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
  return `${base.replace(/\/$/, "")}${path.slice("/api/v1".length)}`;
}
