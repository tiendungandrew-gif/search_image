import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { OperatorWorkspace as App } from "../features/operator/OperatorWorkspace";

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
function stubHealth() {
  const fetch = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(health))),
    );
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

test("renders real health, editable query and explicitly disabled search without retrieval calls", async () => {
  const fetch = stubHealth();
  const user = userEvent.setup();
  render(<App />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Đi từ ý tưởng",
  );
  expect(await screen.findByText("API đang hoạt động")).toBeInTheDocument();
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "a red motorcycle",
  );
  await user.selectOptions(screen.getByLabelText("Phương thức"), "image");
  expect(screen.getByRole("button", { name: /Tìm kiếm ảnh/ })).toBeDisabled();
  expect(screen.getByText(/Tìm kiếm chưa sẵn sàng/)).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/health");
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("shows a safe connection error instead of claiming healthy", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("private endpoint")),
  );
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Chưa kết nối được API",
  );
  expect(screen.getByText("Chưa kết nối API")).toBeInTheDocument();
  expect(screen.queryByText("API đang hoạt động")).not.toBeInTheDocument();
  expect(screen.queryByText("private endpoint")).not.toBeInTheDocument();
});

test("checks actual readiness with session token and renders degraded dependencies", async () => {
  const fetch = stubHealth();
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("API đang hoạt động");
  await user.click(screen.getByText("Kiểm tra hạ tầng"));
  await user.type(
    screen.getByLabelText("Bearer token"),
    "unit-test-session-token",
  );
  fetch.mockImplementationOnce(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({
          status: "not_ready",
          dependencies: {
            postgresql: "healthy",
            qdrant: "unhealthy",
            minio: "healthy",
          },
        }),
        { status: 503 },
      ),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Kiểm tra dịch vụ" }));
  expect(await screen.findByText("Không khả dụng")).toBeInTheDocument();
  expect(fetch.mock.calls[1][1].headers.Authorization).toBe(
    "Bearer unit-test-session-token",
  );
  expect(localStorage.length).toBe(0);
});

test("previews an image locally and never uploads it to a fake search endpoint", async () => {
  const fetch = stubHealth();
  const user = userEvent.setup();
  const { unmount } = render(<App />);
  await screen.findByText("API đang hoạt động");
  const file = new File(["unit-image"], "reference.png", { type: "image/png" });
  await user.upload(screen.getByLabelText(/Thêm ảnh tham chiếu/), file);
  expect(
    await screen.findByAltText("Ảnh tham chiếu xem trước"),
  ).toHaveAttribute("src", "blob:local-preview");
  expect(fetch).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "Bỏ ảnh tham chiếu" }));
  await waitFor(() =>
    expect(screen.queryByRole("img")).not.toBeInTheDocument(),
  );
  unmount();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:local-preview");
});
