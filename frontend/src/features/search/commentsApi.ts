import { api, APIClientError } from "../../services/api/client";
import { record, validAvatarURL, validId } from "../../services/api/decoders";
export interface ImageComment {
  id: string;
  body: string;
  created_at: string;
  can_delete: boolean;
  author: { id: string; display_name: string; avatar_url: string | null };
}
export interface CommentsPage {
  comments: ImageComment[];
  total: number;
  has_more: boolean;
  next_cursor: string | null;
}
function positiveId(value: unknown): value is string {
  return typeof value === "string" && /^[1-9][0-9]{0,18}$/.test(value);
}
function invalid(): never {
  throw new APIClientError(
    "INVALID_RESPONSE",
    "Phản hồi bình luận không hợp lệ.",
  );
}
export function decodeComment(value: unknown): ImageComment {
  if (
    !record(value) ||
    !positiveId(value.id) ||
    typeof value.body !== "string" ||
    value.body.length < 1 ||
    value.body.length > 2000 ||
    typeof value.created_at !== "string" ||
    !Number.isFinite(Date.parse(value.created_at)) ||
    typeof value.can_delete !== "boolean" ||
    !record(value.author) ||
    !validId(value.author.id) ||
    typeof value.author.display_name !== "string" ||
    !validAvatarURL(value.author.avatar_url, value.author.id)
  )
    return invalid();
  return value as unknown as ImageComment;
}
export const commentsAPI = {
  list: (
    imageId: string,
    before?: string,
    signal?: AbortSignal,
  ): Promise<CommentsPage> =>
    api.request(
      `/images/${imageId}/comments${before ? `?before=${before}` : ""}`,
      (value) => {
        if (
          !record(value) ||
          !Array.isArray(value.comments) ||
          value.comments.length > 20 ||
          !Number.isInteger(value.total) ||
          Number(value.total) < 0 ||
          typeof value.has_more !== "boolean" ||
          (value.next_cursor !== null && !positiveId(value.next_cursor)) ||
          (value.has_more && !value.next_cursor)
        )
          return invalid();
        return {
          comments: value.comments.map(decodeComment),
          total: Number(value.total),
          has_more: value.has_more,
          next_cursor: value.next_cursor as string | null,
        };
      },
      { signal },
    ),
  add: (imageId: string, body: string, clientId: string) =>
    api.request(`/images/${imageId}/comments`, decodeComment, {
      json: true,
      body: JSON.stringify({ body, client_id: clientId }),
    }),
  remove: (imageId: string, commentId: string) =>
    api.request(
      `/images/${imageId}/comments/${commentId}`,
      (value) => {
        if (!record(value) || value.status !== "deleted") return invalid();
      },
      { method: "DELETE" },
    ),
};
