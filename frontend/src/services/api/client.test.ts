import { vi } from "vitest";
import { APIClientError, createAPIClient, decodeDiscovery } from "./client";

test("maps a structured authentication error without losing request ID", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHENTICATED",
            message: "Cần token",
            request_id: "request-1",
            retryable: false,
            details: [],
          },
        }),
        { status: 401 },
      ),
    ),
  );
  await expect(createAPIClient().readiness("wrong")).rejects.toMatchObject({
    code: "UNAUTHENTICATED",
    status: 401,
    requestId: "request-1",
  });
});

test("rejects malformed payloads rather than treating them as healthy", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }))),
  );
  await expect(createAPIClient().health()).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});

test("aborts a slow request at the client deadline", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_url, options: RequestInit) =>
        new Promise((_resolve, reject) => {
          options.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
    ),
  );
  const client = createAPIClient("/api/v1", 10);
  await expect(client.health()).rejects.toMatchObject({ code: "TIMEOUT" });
});

test("preserves explicit cancellation separately from network failure", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_url, options: RequestInit) =>
        new Promise((_resolve, reject) => {
          options.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
    ),
  );
  const controller = new AbortController();
  const result = createAPIClient().health(controller.signal);
  controller.abort();
  await expect(result).rejects.toBeInstanceOf(APIClientError);
  await expect(result).rejects.toMatchObject({ code: "ABORTED" });
});

test("search client sends canonical text payload and rejects unsafe image URLs", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        query_id: "test",
        request_id: "req",
        search_mode: "text",
        latency: { processing_ms: 1 },
        warnings: [],
        results: [
          {
            image_id: "one",
            score: 0.4,
            metadata: { tags: [] },
            image_url: "https://untrusted.invalid/image",
            thumbnail_url: "https://untrusted.invalid/image",
          },
        ],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await expect(
    createAPIClient().searchText("coffee", 3, "test-token"),
  ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
    mode: "text",
    text: "coffee",
    top_k: 3,
  });
});

test("advanced client preserves text and image with normalized UI options without a manual multipart boundary", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        query_id: "q",
        request_id: "r",
        search_mode: "multimodal",
        latency: { processing_ms: 1 },
        results: [],
        warnings: [],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  const image = new File(["explicit unit bytes"], "reference.png", {
    type: "image/png",
  });
  await createAPIClient().searchAdvanced(
    {
      mode: "multimodal",
      text: "coffee",
      fusion: { method: "weighted_score", text_weight: 0.3, image_weight: 0.7 },
      rerank: { enabled: true, on_failure: "skip" },
    },
    image,
    "unit-token",
  );
  const options = fetch.mock.calls[0][1];
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/search/multimodal");
  expect(options.headers["Content-Type"]).toBeUndefined();
  expect(options.body.get("image")).toBe(image);
  expect(JSON.parse(options.body.get("options"))).toMatchObject({
    text: "coffee",
    mode: "multimodal",
    fusion: { text_weight: 0.3, image_weight: 0.7 },
    rerank: { enabled: true },
  });
});

test.each([400, 401, 403, 404, 408, 422, 429, 500, 503])(
  "HTTP %s keeps its status even when a proxy returns HTML",
  async (status) => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response("<html>Proxy failure</html>", { status }),
      );
    vi.stubGlobal("fetch", fetch);
    await expect(
      createAPIClient().workspace("unit-token"),
    ).rejects.toMatchObject({ code: "HTTP_ERROR", status });
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

test("discovery validates gallery payloads and rejects duplicate or unsafe images", () => {
  const id = "12345678-1234-4234-8234-123456789abc";
  const item = {
    image_id: id,
    rank: 1,
    score: 0,
    score_type: "cosine",
    image_url: `/api/v1/images/${id}/content?variant=original`,
    thumbnail_url: `/api/v1/images/${id}/content?variant=thumbnail`,
    metadata: {
      title: "Đà Nẵng",
      width: 600,
      height: 400,
      media_type: "image/jpeg",
      tags: [],
      source_dataset: "public",
      city: null,
      license: "CC0",
    },
  };
  expect(
    decodeDiscovery({ results: [item], total_results: 1 }).results[0].image_id,
  ).toBe(id);
  expect(decodeDiscovery({ results: [], total_results: 0 }).results).toEqual(
    [],
  );
  expect(() =>
    decodeDiscovery({ results: [item, item], total_results: 2 }),
  ).toThrow();
  expect(() =>
    decodeDiscovery({
      results: [{ ...item, thumbnail_url: "https://external.test/a.jpg" }],
      total_results: 1,
    }),
  ).toThrow();
  expect(() =>
    decodeDiscovery({ results: [item], total_results: 2 }),
  ).toThrow();
});
