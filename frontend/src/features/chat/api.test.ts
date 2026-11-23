import { decodeMessage, decodeChatUser } from "./api";
const id = "12345678-1234-4234-8234-123456789abc";
const message = {
  id: "9007199254740992",
  sender_id: id,
  client_id: id,
  body: "Hello",
  created_at: "2026-11-23T10:00:00Z",
  image_url: "/api/v1/chat/attachments/9007199254740992",
};
test("chat message ids retain precision and attachment URLs stay same origin", () => {
  expect(decodeMessage(message).id).toBe("9007199254740992");
  expect(() =>
    decodeMessage({
      ...message,
      image_url: "https://outside.example/image.jpg",
    }),
  ).toThrow();
  expect(() =>
    decodeMessage({ ...message, image_url: "/api/v1/chat/attachments/1" }),
  ).toThrow();
  expect(() => decodeMessage({ ...message, id: 1 })).toThrow();
  expect(() => decodeMessage({ ...message, sender_id: "invalid" })).toThrow();
});
test("account search validates public chat identity", () => {
  expect(
    decodeChatUser({ id, username: "alice", display_name: "Alice" }).username,
  ).toBe("alice");
  expect(() =>
    decodeChatUser({ id: "invalid", username: "alice", display_name: "Alice" }),
  ).toThrow();
});
