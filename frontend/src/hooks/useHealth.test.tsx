import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";
import { api } from "../services/api/client";
import { useHealth } from "./useHealth";

test("unmount cancels the current manual refresh, including a superseded initial request", () => {
  const calls: AbortSignal[] = [];
  vi.spyOn(api, "health").mockImplementation((signal) => {
    calls.push(signal!);
    return new Promise(() => {});
  });
  const { result, unmount } = renderHook(() => useHealth());
  act(() => {
    void result.current.refresh();
  });
  expect(calls[0].aborted).toBe(true);
  expect(calls[1].aborted).toBe(false);
  unmount();
  expect(calls[1].aborted).toBe(true);
});
