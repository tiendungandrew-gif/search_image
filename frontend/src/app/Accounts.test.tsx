import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { App } from "./App";
const id = "12345678-1234-4234-8234-123456789abc";
function setup(role: "user" | "admin" | null) {
  const account = role
    ? {
        id,
        username: "reader",
        display_name: "Người dùng",
        role,
        is_active: true,
        datasets: [{ id, key: "private", name: "Thư viện riêng" }],
      }
    : null;
  const health = {
    status: "ok",
    check: "live",
    capabilities: {
      text_search: false,
      image_search: false,
      multimodal: false,
      multi_intent: false,
      rerank: false,
      explanations: false,
      agent: false,
    },
    worker: { state: "unknown" },
  };
  const fetch = vi.fn(
    async (url: string) =>
      new Response(
        JSON.stringify(
          url.includes("/health")
            ? health
            : url.includes("/chat/conversations")
              ? { conversations: [] }
              : { user: account, legacy_enabled: false },
        ),
      ),
  );
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => history.replaceState(null, "", "/"));
test("anonymous visitors explore public search and can open sign in without a token", async () => {
  setup(null);
  render(<App />);
  expect(
    await screen.findByRole("link", { name: "Đăng nhập" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Thư viện riêng")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("link", { name: "Đăng nhập" }));
  expect(
    await screen.findByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText(/token/i)).not.toBeInTheDocument();
});
test("members see assigned libraries and cannot open admin by URL", async () => {
  setup("user");
  history.replaceState(null, "", "/admin");
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Bạn không có quyền quản trị" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Quản trị" }),
  ).not.toBeInTheDocument();
});
test("member search has no credentials or infrastructure controls", async () => {
  setup("user");
  render(<App />);
  expect(
    await screen.findByRole("button", { name: "Mở tin nhắn" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Quản trị" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Kiểm tra hạ tầng")).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/token/i)).not.toBeInTheDocument();
});
test("admins see management navigation and sign out without storing credentials", async () => {
  const fetch = setup("admin");
  render(<App />);
  expect(
    await screen.findByRole("link", { name: "Quản trị" }),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByLabelText(/Menu tài khoản của/));
  await userEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
  expect(
    await screen.findByRole("link", { name: "Đăng nhập" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Thư viện riêng")).not.toBeInTheDocument();
  expect(fetch.mock.calls.some(([url]) => url.endsWith("/auth/logout"))).toBe(
    true,
  );
  expect(localStorage.getItem("lens.token")).toBeNull();
});
