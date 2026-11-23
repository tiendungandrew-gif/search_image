import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import ChatWidget from "./ChatWidget";
import { chatAPI, type ChatMessage } from "./api";

vi.mock("./api", () => ({
  chatAPI: {
    conversations: vi.fn(),
    users: vi.fn(),
    start: vi.fn(),
    messages: vi.fn(),
    read: vi.fn(),
    send: vi.fn(),
  },
}));
const own = {
  id: "12345678-1234-4234-8234-123456789abc",
  username: "alice",
  display_name: "Alice",
  role: "user" as const,
  is_active: true,
  datasets: [],
};
const peer = {
  id: "22345678-1234-4234-8234-123456789abc",
  username: "bob",
  display_name: "Bob",
};
const conversation = {
  id: "32345678-1234-4234-8234-123456789abc",
  peer,
  unread: 1,
  last_message: null,
  updated_at: "2026-11-23T10:00:00Z",
};
const msg: ChatMessage = {
  id: "1",
  sender_id: own.id,
  client_id: "42345678-1234-4234-8234-123456789abc",
  body: "Xin chào",
  image_url: null,
  created_at: "2026-11-23T10:00:00Z",
};
beforeEach(() => {
  vi.mocked(chatAPI.conversations).mockResolvedValue([conversation]);
  vi.mocked(chatAPI.messages).mockResolvedValue({
    messages: [],
    has_more: false,
  });
  vi.mocked(chatAPI.read).mockResolvedValue(undefined);
  vi.mocked(chatAPI.users).mockResolvedValue([peer]);
  vi.mocked(chatAPI.start).mockResolvedValue({ id: conversation.id, peer });
  Element.prototype.scrollTo = vi.fn();
});
afterEach(() => vi.resetAllMocks());

test("guest menu offers sign in without accessing private chat APIs", async () => {
  const user = userEvent.setup();
  render(<ChatWidget user={null} />);
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute(
    "href",
    "/login",
  );
  expect(chatAPI.conversations).not.toHaveBeenCalled();
});

test("menu shows unread conversations, sends text and appends server-confirmed messages", async () => {
  vi.mocked(chatAPI.send).mockResolvedValue(msg);
  const user = userEvent.setup();
  render(<ChatWidget user={own} />);
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  await user.click(await screen.findByRole("button", { name: /Bob/ }));
  await user.type(
    screen.getByRole("textbox", { name: "Nhập tin nhắn" }),
    "Xin chào",
  );
  await user.click(screen.getByRole("button", { name: "Gửi ↑" }));
  expect(await screen.findByText("Xin chào")).toBeVisible();
  expect(chatAPI.send).toHaveBeenCalledWith(
    conversation.id,
    "Xin chào",
    null,
    expect.any(String),
  );
  expect(screen.getByRole("textbox", { name: "Nhập tin nhắn" })).toHaveValue(
    "",
  );
});

test("failed sends retain draft and idempotency key for a safe retry", async () => {
  vi.mocked(chatAPI.send)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(msg);
  const user = userEvent.setup();
  render(<ChatWidget user={own} />);
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  await user.click(await screen.findByRole("button", { name: /Bob/ }));
  await user.type(
    screen.getByRole("textbox", { name: "Nhập tin nhắn" }),
    "Xin chào",
  );
  await user.click(screen.getByRole("button", { name: "Gửi ↑" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("offline");
  expect(screen.getByRole("textbox", { name: "Nhập tin nhắn" })).toHaveValue(
    "Xin chào",
  );
  await user.click(screen.getByRole("button", { name: "Gửi ↑" }));
  expect(chatAPI.send).toHaveBeenCalledTimes(2);
  expect(vi.mocked(chatAPI.send).mock.calls[0][3]).toBe(
    vi.mocked(chatAPI.send).mock.calls[1][3],
  );
});

test("new message finds another user and opens the shared conversation", async () => {
  const user = userEvent.setup();
  render(<ChatWidget user={own} />);
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  await user.click(screen.getByRole("button", { name: "Tin nhắn mới" }));
  await user.type(
    screen.getByRole("textbox", { name: "Tìm người dùng" }),
    "bob",
  );
  await user.click(await screen.findByRole("button", { name: /@bob/ }));
  expect(chatAPI.start).toHaveBeenCalledWith(peer.id);
  expect(screen.getByRole("textbox", { name: "Nhập tin nhắn" })).toBeVisible();
});

test("unsupported attachments are rejected before uploading", async () => {
  const user = userEvent.setup();
  const { container } = render(<ChatWidget user={own} />);
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  await user.click(await screen.findByRole("button", { name: /Bob/ }));
  const file = new File(["<svg/>"], "unsafe.svg", { type: "image/svg+xml" });
  fireEvent.change(container.querySelector('input[type="file"]')!, {
    target: { files: [file] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent("JPEG, PNG hoặc WebP");
  expect(chatAPI.send).not.toHaveBeenCalled();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Gửi ↑" })).toBeDisabled(),
  );
});

test("sidebar notifications show unread chats and open the selected thread", async () => {
  vi.mocked(chatAPI.conversations).mockResolvedValue([
    conversation,
    {
      ...conversation,
      id: "52345678-1234-4234-8234-123456789abc",
      peer: { ...peer, display_name: "Carol" },
      unread: 0,
    },
  ]);
  const user = userEvent.setup();
  render(<ChatWidget user={own} rail />);
  await user.click(screen.getByRole("button", { name: "Thông báo" }));
  await screen.findByRole("button", { name: /Bob/ });
  expect(
    screen.queryByRole("button", { name: /Carol/ }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Tin nhắn mới" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Bob/ }));
  expect(screen.getByRole("textbox", { name: "Nhập tin nhắn" })).toBeVisible();
});

test("docked inbox stays open while browsing content and closes explicitly", async () => {
  const user = userEvent.setup();
  render(
    <div>
      <ChatWidget user={own} rail />
      <button type="button">Xem ảnh</button>
    </div>,
  );
  await user.click(screen.getByRole("button", { name: "Mở tin nhắn" }));
  await user.click(screen.getByRole("button", { name: "Xem ảnh" }));
  expect(
    screen.getByRole("complementary", { name: "Tin nhắn riêng" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Đóng tin nhắn" }));
  expect(
    screen.queryByRole("complementary", { name: "Tin nhắn riêng" }),
  ).not.toBeInTheDocument();
});
