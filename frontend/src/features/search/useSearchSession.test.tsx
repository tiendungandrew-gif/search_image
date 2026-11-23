import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";
import { api } from "../../services/api/client";
import type { SearchResponse } from "../../types/api";
import { useSearchSession } from "./useSearchSession";

const response = (id: string) =>
  ({
    query_id: id,
    results: [{ image_id: id }],
    total_results: 1,
  }) as SearchResponse;
const input = { mode: "text", text: "coffee" } as const;
const options = { includeExplanation: false, planner: "deterministic" };
test("a superseded request cannot replace newer results or loading state", async () => {
  let resolveFirst: (value: SearchResponse) => void = () => {};
  let resolveSecond: (value: SearchResponse) => void = () => {};
  const call = vi
    .spyOn(api, "searchAdvanced")
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    )
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSecond = resolve;
        }),
    );
  const { result } = renderHook(() => useSearchSession("unit-token"));
  let first!: Promise<void>, second!: Promise<void>;
  act(() => {
    first = result.current.execute(input, null, options);
  });
  act(() => {
    second = result.current.execute(input, null, options);
  });
  expect(call.mock.calls[0][3]?.aborted).toBe(true);
  await act(async () => {
    resolveFirst(response("old"));
    await first;
  });
  expect(result.current.state).toBe("SEARCHING");
  await act(async () => {
    resolveSecond(response("new"));
    await second;
  });
  expect(result.current.results?.query_id).toBe("new");
  expect(result.current.state).toBe("SUCCESS");
});
test("cancel and token replacement discard late responses", async () => {
  let resolve: (value: SearchResponse) => void = () => {};
  vi.spyOn(api, "searchAdvanced").mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const { result, rerender } = renderHook(
    ({ token }) => useSearchSession(token),
    { initialProps: { token: "one" } },
  );
  let pending!: Promise<void>;
  act(() => {
    pending = result.current.execute(input, null, options);
  });
  act(() => result.current.cancel());
  await act(async () => {
    resolve(response("late"));
    await pending;
  });
  expect(result.current.state).toBe("CANCELLED");
  expect(result.current.results).toBeNull();
  act(() => {
    pending = result.current.execute(input, null, options);
  });
  rerender({ token: "two" });
  await act(async () => {
    resolve(response("wrong-token"));
    await pending;
  });
  expect(result.current.results).toBeNull();
  expect(result.current.state).toBe("IDLE");
});

test("paging reuses submitted query, filters and image; new search starts at page one", async () => {
  const paged = {
    ...response("page"),
    pagination: {
      page: 1,
      page_size: 10,
      total_results: 25,
      total_pages: 3,
      result_limit: 500,
    },
  };
  const call = vi.spyOn(api, "searchAdvanced").mockResolvedValue(paged);
  const image = new File(["image"], "reference.jpg", { type: "image/jpeg" });
  const submitted = {
    mode: "multimodal" as const,
    text: "phở",
    top_k: 10,
    filters: { city: "Hà Nội" },
  };
  const { result } = renderHook(() => useSearchSession("unit-token"));
  await act(async () => {
    await result.current.execute(submitted, image, options);
  });
  await act(async () => {
    await result.current.goToPage(2);
  });
  expect(call.mock.calls.at(-1)?.[0]).toEqual({ ...submitted, page: 2 });
  expect(call.mock.calls.at(-1)?.[1]).toBe(image);
  const count = call.mock.calls.length;
  await act(async () => {
    await result.current.goToPage(4);
  });
  expect(call).toHaveBeenCalledTimes(count);
  await act(async () => {
    await result.current.execute({ mode: "text", text: "biển" }, null, options);
  });
  expect(call.mock.calls.at(-1)?.[0]).toEqual({
    mode: "text",
    text: "biển",
    page: 1,
  });
});
