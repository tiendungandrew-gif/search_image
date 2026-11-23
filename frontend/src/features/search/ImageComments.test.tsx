import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { vi } from "vitest";
import { CurrentAccountContext } from "../auth/CurrentAccountContext";
import { ImageComments } from "./ImageComments";
import {
  commentsAPI,
  type CommentsPage,
  type ImageComment,
} from "./commentsApi";
vi.mock("./commentsApi", () => ({
  commentsAPI: { list: vi.fn(), add: vi.fn(), remove: vi.fn() },
}));
const id = "12345678-1234-4234-8234-123456789abc";
const user = {
  id,
  username: "alice",
  display_name: "Alice",
  role: "user" as const,
  is_active: true,
  datasets: [],
};
const comment: ImageComment = {
  id: "1",
  body: "Ảnh đẹp!",
  created_at: "2026-11-23T09:00:00Z",
  can_delete: true,
  author: { id, display_name: "Alice", avatar_url: null },
};
const empty: CommentsPage = {
  comments: [],
  total: 0,
  has_more: false,
  next_cursor: null,
};
beforeEach(() => {
  vi.mocked(commentsAPI.list).mockResolvedValue(empty);
  vi.mocked(commentsAPI.remove).mockResolvedValue(undefined);
});
afterEach(() => vi.resetAllMocks());
function setup() {
  return render(
    <CurrentAccountContext.Provider value={user}>
      <ImageComments imageId={id} />
    </CurrentAccountContext.Provider>,
  );
}
test("signed-in users can post plain text and remove their comment", async () => {
  vi.mocked(commentsAPI.add).mockResolvedValue({
    ...comment,
    body: "<script>alert(1)</script>",
  });
  const { container } = setup();
  await screen.findByText(/Chưa có bình luận/);
  fireEvent.change(screen.getByRole("textbox", { name: "Viết bình luận" }), {
    target: { value: "<script>alert(1)</script>" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Gửi bình luận" }));
  expect(await screen.findByText("<script>alert(1)</script>")).toBeVisible();
  expect(container.querySelector("script")).toBeNull();
  expect(screen.getByRole("textbox")).toHaveValue("");
  fireEvent.click(
    screen.getByRole("button", { name: "Xóa bình luận của Alice" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByText("<script>alert(1)</script>"),
    ).not.toBeInTheDocument(),
  );
  expect(commentsAPI.remove).toHaveBeenCalledWith(id, "1");
});
test("retrying a failed send preserves the draft and client nonce", async () => {
  vi.mocked(commentsAPI.add)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(comment);
  setup();
  await screen.findByText(/Chưa có bình luận/);
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Ảnh đẹp!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Gửi bình luận" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("offline");
  expect(screen.getByRole("textbox")).toHaveValue("Ảnh đẹp!");
  fireEvent.click(screen.getByRole("button", { name: "Gửi bình luận" }));
  await screen.findByText("Ảnh đẹp!");
  expect(vi.mocked(commentsAPI.add).mock.calls[0][2]).toBe(
    vi.mocked(commentsAPI.add).mock.calls[1][2],
  );
});
test("guests can read public comments but must sign in to post", async () => {
  vi.mocked(commentsAPI.list).mockResolvedValue({
    ...empty,
    comments: [comment],
    total: 1,
  });
  render(<ImageComments imageId={id} />);
  expect(await screen.findByText("Ảnh đẹp!")).toBeVisible();
  expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute(
    "href",
    "/login",
  );
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Xóa bình luận của Alice" }),
  ).not.toBeInTheDocument();
});
test("older pages append without duplicating comments", async () => {
  vi.mocked(commentsAPI.list)
    .mockResolvedValueOnce({
      comments: [{ ...comment, id: "2" }],
      total: 2,
      has_more: true,
      next_cursor: "2",
    })
    .mockResolvedValueOnce({
      comments: [comment],
      total: 2,
      has_more: false,
      next_cursor: null,
    });
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Xem bình luận trước đó" }),
  );
  await waitFor(() => expect(screen.getAllByText("Ảnh đẹp!")).toHaveLength(2));
  expect(commentsAPI.list).toHaveBeenLastCalledWith(id, "2");
  expect(
    screen.queryByRole("button", { name: "Xem bình luận trước đó" }),
  ).not.toBeInTheDocument();
});
test("switching images ignores a late response for the previous image", async () => {
  let resolve!: (page: CommentsPage) => void;
  vi.mocked(commentsAPI.list)
    .mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    )
    .mockResolvedValueOnce(empty);
  const { rerender } = render(<ImageComments key="first" imageId={id} />);
  const signal = vi.mocked(commentsAPI.list).mock.calls[0][2];
  rerender(
    <ImageComments
      key="second"
      imageId="22345678-1234-4234-8234-123456789abc"
    />,
  );
  expect(signal?.aborted).toBe(true);
  await screen.findByText(/Chưa có bình luận/);
  await act(async () =>
    resolve({
      comments: [comment],
      total: 1,
      has_more: false,
      next_cursor: null,
    }),
  );
  expect(screen.queryByText("Ảnh đẹp!")).not.toBeInTheDocument();
});
