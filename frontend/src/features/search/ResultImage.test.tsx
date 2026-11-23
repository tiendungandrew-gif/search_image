import { act, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { ResultImage } from "./ResultImage";
const url =
  "/api/v1/images/30000000-0000-4000-8000-000000000001/content?variant=thumbnail";
test("image network fetch waits for intersection, and unmount aborts it", async () => {
  let intersect!: (entries: { isIntersecting: boolean }[]) => void;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: typeof intersect) {
        intersect = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  const fetch = vi.fn().mockImplementation(() => new Promise(() => {}));
  vi.stubGlobal("fetch", fetch);
  const { unmount } = render(
    <ResultImage url={url} token="unit" alt="Test photo" />,
  );
  expect(fetch).not.toHaveBeenCalled();
  act(() => intersect([{ isIntersecting: true }]));
  expect(fetch).toHaveBeenCalledTimes(1);
  unmount();
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
});
test("unsafe image paths are rejected without disclosing a bearer token", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  render(
    <ResultImage
      eager
      url="https://untrusted.invalid/pixel"
      token="unit"
      alt="Photo"
    />,
  );
  await waitFor(() =>
    expect(screen.getByText("Đường dẫn ảnh không hợp lệ.")).toBeInTheDocument(),
  );
  expect(fetch).not.toHaveBeenCalled();
});
