import { decodeComment } from "./commentsApi";
const id = "12345678-1234-4234-8234-123456789abc";
const comment = {
  id: "9007199254740992",
  body: "Hello",
  created_at: "2026-11-23T09:00:00Z",
  can_delete: false,
  author: { id, display_name: "Alice", avatar_url: null },
};
test("comment ids keep precision and plain text remains plain text", () => {
  expect(decodeComment(comment).id).toBe("9007199254740992");
  expect(decodeComment({ ...comment, body: "<b>Hello</b>" }).body).toBe(
    "<b>Hello</b>",
  );
});
test("rejects unsafe avatars, invalid authors and malformed text", () => {
  expect(() =>
    decodeComment({
      ...comment,
      author: {
        ...comment.author,
        avatar_url: "https://external.example/a.jpg",
      },
    }),
  ).toThrow();
  expect(() => decodeComment({ ...comment, body: "x".repeat(2001) })).toThrow();
  expect(() => decodeComment({ ...comment, id: -1 })).toThrow();
});
