import { api, APIClientError } from "../../services/api/client";
import { record, validId, validAvatarURL } from "../../services/api/decoders";
export interface ChatUser {
  avatar_url?: string | null;
  id: string;
  username: string;
  display_name: string;
}
export interface ChatMessage {
  id: string;
  sender_id: string;
  client_id: string;
  body: string;
  created_at: string;
  image_url: string | null;
}
export interface Conversation {
  id: string;
  peer: ChatUser;
  unread: number;
  last_message: ChatMessage | null;
  updated_at: string;
}
const invalid = (): never => {
  throw new APIClientError(
    "INVALID_RESPONSE",
    "Phản hồi trò chuyện không hợp lệ.",
  );
};
export function decodeChatUser(value: unknown): ChatUser {
  if (
    !record(value) ||
    !validId(value.id) ||
    typeof value.username !== "string" ||
    typeof value.display_name !== "string" ||
    !validAvatarURL(value.avatar_url, value.id)
  )
    return invalid();
  return value as unknown as ChatUser;
}
export function decodeMessage(value: unknown): ChatMessage {
  if (
    !record(value) ||
    typeof value.id !== "string" ||
    !/^[1-9][0-9]{0,18}$/.test(value.id) ||
    !validId(value.sender_id) ||
    !validId(value.client_id) ||
    typeof value.body !== "string" ||
    value.body.length > 4000 ||
    typeof value.created_at !== "string" ||
    !Number.isFinite(Date.parse(value.created_at)) ||
    (value.image_url !== null &&
      value.image_url !== `/api/v1/chat/attachments/${value.id}`)
  )
    return invalid();
  return value as unknown as ChatMessage;
}
export const chatAPI = {
  users: (q: string, signal?: AbortSignal): Promise<ChatUser[]> =>
    api.request(
      `/chat/users?q=${encodeURIComponent(q)}`,
      (value) => {
        if (
          !record(value) ||
          !Array.isArray(value.users) ||
          value.users.length > 20
        )
          return invalid();
        return value.users.map(decodeChatUser);
      },
      { signal },
    ),
  conversations: (signal?: AbortSignal): Promise<Conversation[]> =>
    api.request(
      "/chat/conversations",
      (value) => {
        if (
          !record(value) ||
          !Array.isArray(value.conversations) ||
          value.conversations.length > 100
        )
          return invalid();
        return value.conversations.map((item) => {
          if (
            !record(item) ||
            !validId(item.id) ||
            !Number.isInteger(item.unread) ||
            Number(item.unread) < 0 ||
            typeof item.updated_at !== "string"
          )
            return invalid();
          return {
            id: item.id as string,
            peer: decodeChatUser(item.peer),
            unread: Number(item.unread),
            last_message:
              item.last_message === null
                ? null
                : decodeMessage(item.last_message),
            updated_at: item.updated_at,
          };
        });
      },
      { signal },
    ),
  start: (userId: string): Promise<{ id: string; peer: ChatUser }> =>
    api.request(
      "/chat/conversations",
      (value) => {
        if (!record(value) || !validId(value.id)) return invalid();
        return { id: value.id as string, peer: decodeChatUser(value.peer) };
      },
      { json: true, body: JSON.stringify({ user_id: userId }) },
    ),
  messages: (
    id: string,
    cursor: { before?: string; after?: string } = {},
    signal?: AbortSignal,
  ): Promise<{ messages: ChatMessage[]; has_more: boolean }> => {
    const params = new URLSearchParams(cursor);
    return api.request(
      `/chat/conversations/${id}/messages?${params}`,
      (value) => {
        if (
          !record(value) ||
          !Array.isArray(value.messages) ||
          value.messages.length > 50 ||
          typeof value.has_more !== "boolean"
        )
          return invalid();
        return {
          messages: value.messages.map(decodeMessage),
          has_more: value.has_more,
        };
      },
      { signal },
    );
  },
  read: (id: string, messageId: string) =>
    api.request(`/chat/conversations/${id}/read`, () => undefined, {
      json: true,
      body: JSON.stringify({ message_id: messageId }),
    }),
  send: (
    id: string,
    body: string,
    image: File | null,
    clientId: string,
  ): Promise<ChatMessage> => {
    const data = new FormData();
    data.set("body", body);
    data.set("client_id", clientId);
    if (image) data.set("image", image);
    return api.request(`/chat/conversations/${id}/messages`, decodeMessage, {
      body: data,
      method: "POST",
      timeout: 30_000,
    });
  },
};
