import { act, renderHook, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { api } from "../../services/api/client";
import type { DiscoveryResponse } from "../../types/api";
import { useDiscovery } from "./useDiscovery";

const response = (id: string) =>
  ({
    total_results: id.length,
    results: [],
  }) as unknown as DiscoveryResponse;

test("discovery waits for a ready library and respects its result limit", async () => {
  const search = vi
    .spyOn(api, "discovery")
    .mockResolvedValue(response("scoped"));
  const { result, rerender } = renderHook(
    ({ enabled }) => useDiscovery(enabled, "member", 5),
    { initialProps: { enabled: false } },
  );
  expect(search).not.toHaveBeenCalled();
  rerender({ enabled: true });
  await waitFor(() =>
    expect(result.current.results?.total_results).toBe("scoped".length),
  );
  expect(search).toHaveBeenCalledWith(5, "member", expect.any(AbortSignal));
  rerender({ enabled: true });
  expect(search).toHaveBeenCalledTimes(1);
});

test("changing credentials hides old photos and rejects a late response", async () => {
  const pending: ((value: DiscoveryResponse) => void)[] = [];
  const search = vi
    .spyOn(api, "discovery")
    .mockImplementation(() => new Promise((resolve) => pending.push(resolve)));
  const { result, rerender, unmount } = renderHook(
    ({ token }) => useDiscovery(true, token),
    { initialProps: { token: "first" } },
  );
  rerender({ token: "second" });
  expect(search.mock.calls[0][2]?.aborted).toBe(true);
  await act(async () => pending[0](response("wrong-account")));
  expect(result.current.results).toBeNull();
  await act(async () => pending[1](response("current-account")));
  expect(result.current.results?.total_results).toBe("current-account".length);
  rerender({ token: "third" });
  expect(result.current.results).toBeNull();
  unmount();
  expect(search.mock.calls[2][2]?.aborted).toBe(true);
});

test("failed previews wait for an explicit retry", async () => {
  const search = vi
    .spyOn(api, "discovery")
    .mockRejectedValueOnce(new Error("Temporarily unavailable"))
    .mockResolvedValue(response("retry"));
  const { result } = renderHook(() => useDiscovery(true, "member"));
  await waitFor(() =>
    expect(result.current.error).toBe("Temporarily unavailable"),
  );
  expect(search).toHaveBeenCalledTimes(1);
  act(() => result.current.retry());
  await waitFor(() =>
    expect(result.current.results?.total_results).toBe("retry".length),
  );
  expect(result.current.error).toBeNull();
  expect(search).toHaveBeenCalledTimes(2);
});

test("a new visit fetches another sample instead of reusing the previous gallery", async () => {
  const search = vi
    .spyOn(api, "discovery")
    .mockResolvedValueOnce(response("first"))
    .mockResolvedValueOnce(response("another-visit"));
  const first = renderHook(() => useDiscovery(true, "member"));
  await waitFor(() =>
    expect(first.result.current.results?.total_results).toBe(5),
  );
  first.unmount();
  const second = renderHook(() => useDiscovery(true, "member"));
  await waitFor(() =>
    expect(second.result.current.results?.total_results).toBe(13),
  );
  expect(search).toHaveBeenCalledTimes(2);
});

test("loads another page once, appends unique images and stops at the end", async () => {
  const seed = "12345678-1234-4234-8234-123456789abc";
  const image = (id: string) =>
    ({ image_id: id, rank: 1 }) as DiscoveryResponse["results"][number];
  const first: DiscoveryResponse = {
    seed,
    has_more: true,
    next_cursor: "cursor1",
    total_results: 1,
    results: [image("first")],
  };
  let complete!: (page: DiscoveryResponse) => void;
  const search = vi
    .spyOn(api, "discovery")
    .mockResolvedValueOnce(first)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
  const { result } = renderHook(() => useDiscovery(true, "member"));
  await waitFor(() => expect(result.current.hasMore).toBe(true));
  act(() => {
    void result.current.loadMore();
    void result.current.loadMore();
  });
  expect(search).toHaveBeenCalledTimes(2);
  expect(search).toHaveBeenLastCalledWith(
    24,
    "member",
    expect.any(AbortSignal),
    { seed, cursor: "cursor1" },
  );
  await act(async () =>
    complete({
      seed,
      has_more: false,
      next_cursor: null,
      total_results: 2,
      results: [image("first"), image("second")],
    }),
  );
  expect(result.current.results?.results.map((item) => item.image_id)).toEqual([
    "first",
    "second",
  ]);
  expect(result.current.hasMore).toBe(false);
  expect(result.current.loadingMore).toBe(false);
  await act(async () => result.current.loadMore());
  expect(search).toHaveBeenCalledTimes(2);
});

test("a pagination failure keeps existing images and retries the same cursor", async () => {
  const first: DiscoveryResponse = {
    seed: "seed",
    has_more: true,
    next_cursor: "cursor",
    results: [],
    total_results: 0,
  };
  const search = vi
    .spyOn(api, "discovery")
    .mockResolvedValueOnce(first)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ ...first, has_more: false, next_cursor: null });
  const { result } = renderHook(() => useDiscovery(true, "member"));
  await waitFor(() => expect(result.current.hasMore).toBe(true));
  await act(async () => result.current.loadMore());
  expect(result.current.results).toEqual(first);
  expect(result.current.moreError).toBe("offline");
  await act(async () => result.current.loadMore());
  expect(result.current.moreError).toBeNull();
  expect(search.mock.calls[1][3]).toEqual(search.mock.calls[2][3]);
});
