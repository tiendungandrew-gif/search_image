import {
  api,
  APIClientError,
  decodeDiscovery,
} from "../../services/api/client";
import { record, validId } from "../../services/api/decoders";
import { decodeAuth } from "../auth/api";
import type { Account } from "../../types/access";
import type { SearchResult } from "../../types/api";
export interface Profile {
  user: Account;
  bio: string;
  created_at: string;
  favorite_count: number;
}
export function decodeProfile(value: unknown): Profile {
  if (
    !record(value) ||
    typeof value.bio !== "string" ||
    value.bio.length > 500 ||
    typeof value.created_at !== "string" ||
    !Number.isInteger(value.favorite_count) ||
    Number(value.favorite_count) < 0
  )
    throw new APIClientError("INVALID_RESPONSE", "Hồ sơ không hợp lệ.");
  const auth = decodeAuth({ user: value.user, legacy_enabled: false });
  if (!auth.user)
    throw new APIClientError("INVALID_RESPONSE", "Hồ sơ không hợp lệ.");
  return { ...value, user: auth.user } as unknown as Profile;
}
export const profileAPI = {
  me: (signal?: AbortSignal) =>
    api.request("/profile", decodeProfile, { signal }),
  update: (display_name: string, bio: string) =>
    api.request("/profile", decodeProfile, {
      method: "PATCH",
      json: true,
      body: JSON.stringify({ display_name, bio }),
    }),
  avatar: (image: File) => {
    const body = new FormData();
    body.set("image", image);
    return api.request("/profile/avatar", decodeProfile, {
      method: "POST",
      body,
      timeout: 30_000,
    });
  },
  status: (ids: string[], signal?: AbortSignal): Promise<string[]> => {
    const params = new URLSearchParams();
    for (const id of ids) params.append("ids", id);
    return api.request(
      `/profile/favorites/status?${params}`,
      (value) => {
        if (
          !record(value) ||
          !Array.isArray(value.ids) ||
          value.ids.length > 50 ||
          !value.ids.every((id) => validId(id) && ids.includes(id))
        )
          throw new APIClientError(
            "INVALID_RESPONSE",
            "Trạng thái yêu thích không hợp lệ.",
          );
        return value.ids as string[];
      },
      { signal },
    );
  },
  save: (id: string, saved: boolean) =>
    api.request(
      `/profile/favorites/${id}`,
      (value) => {
        if (!record(value) || value.saved !== saved)
          throw new APIClientError(
            "INVALID_RESPONSE",
            "Chưa lưu được trạng thái yêu thích.",
          );
      },
      { method: saved ? "PUT" : "DELETE" },
    ),
  favorites: (
    before?: string,
    signal?: AbortSignal,
  ): Promise<{
    results: SearchResult[];
    total_saved: number;
    has_more: boolean;
    next_cursor: string | null;
  }> =>
    api.request(
      `/profile/favorites?limit=24${before ? `&before=${encodeURIComponent(before)}` : ""}`,
      (value) => {
        const decoded = decodeDiscovery(
          record(value)
            ? { results: value.results, total_results: value.total_results }
            : value,
        );
        if (
          !record(value) ||
          !Number.isInteger(value.total_saved) ||
          Number(value.total_saved) < 0 ||
          typeof value.has_more !== "boolean" ||
          (value.next_cursor !== null &&
            (typeof value.next_cursor !== "string" ||
              !/^\d+$/.test(value.next_cursor)))
        )
          throw new APIClientError(
            "INVALID_RESPONSE",
            "Danh sách yêu thích không hợp lệ.",
          );
        return {
          ...decoded,
          total_saved: Number(value.total_saved),
          has_more: value.has_more,
          next_cursor: value.next_cursor as string | null,
        };
      },
      { signal },
    ),
};
