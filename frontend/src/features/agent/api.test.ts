import { vi } from "vitest";
import { decodeAgent, searchAgent } from "./api";

const id = "30000000-0000-4000-8000-000000000001";
export function fixture() {
  return {
    query_id: "unit",
    status: "completed",
    query_success: true,
    dataset_status: "available",
    results: [
      {
        image_id: id,
        rank: 1,
        score: 0.2,
        score_type: "cosine",
        image_url: `/api/v1/images/${id}/content?variant=original`,
        thumbnail_url: `/api/v1/images/${id}/content?variant=thumbnail`,
        metadata: {
          title: "Unit fixture",
          caption: null,
          width: 8,
          height: 8,
          media_type: "image/png",
          tags: [],
          source_dataset: "fixture",
          city: null,
          license: "fixture",
        },
      },
    ],
    steps: [],
    latency_ms: 1,
    logical_hops: 1,
    tool_calls: 1,
    warnings: [],
    error_code: null,
    relationship_summary: null,
    rag: null,
  };
}

test("chunked UTF-8 SSE displays only public progress and validates the final result", async () => {
  const bytes = new TextEncoder().encode(
    [
      'event: planning_started\r\ndata: {"note":"Kế hoạch"}\r\n\r\n',
      'event: token\r\ndata: {"text":"unverified","verified":false}\r\n\r\n',
      `event: agent_completed\r\ndata: ${JSON.stringify(fixture())}\r\n\r\n`,
    ].join(""),
  );
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += 3)
        controller.enqueue(bytes.slice(i, i + 3));
      controller.close();
    },
  });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(stream, {
        headers: { "content-type": "text/event-stream" },
      }),
    ),
  );
  const progress = vi.fn();
  const result = await searchAgent(
    { query: "unit" },
    "unit-token",
    new AbortController().signal,
    progress,
  );
  expect(result.results[0].image_id).toBe(id);
  expect(progress).toHaveBeenCalledTimes(1);
  expect(progress.mock.calls[0][0]).toBe("planning_started");
});

test("an incomplete stream is rejected instead of inventing a final answer", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response("event: planning_started\ndata: {}\n\n", {
        headers: { "content-type": "text/event-stream" },
      }),
    ),
  );
  await expect(
    searchAgent(
      { query: "unit" },
      "unit",
      new AbortController().signal,
      vi.fn(),
    ),
  ).rejects.toThrow("chưa có kết quả");
});

test("foreign image URLs and unsupported image citations are rejected", () => {
  const value = fixture();
  value.results[0].thumbnail_url = "https://external.invalid/image";
  expect(() => decodeAgent(value)).toThrow("không đúng định dạng");
  const wrong = {
    ...fixture(),
    rag: {
      answer: "bad",
      citations: [{ image_id: "unknown", quote: "bad" }],
      error_code: null,
    },
  };
  expect(() => decodeAgent(wrong)).toThrow("không đúng định dạng");
});

test("optional RAG errors do not discard the validated partial image result", async () => {
  const partial = {
    ...fixture(),
    status: "partial",
    query_success: false,
    warnings: ["LLM_RATE_LIMITED"],
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          'event: error\ndata: {"code":"LLM_RATE_LIMITED","retrieval_preserved":true}\n\n' +
            `event: agent_partial\ndata: ${JSON.stringify(partial)}\n\n`,
          { headers: { "content-type": "text/event-stream" } },
        ),
      ),
  );
  const response = await searchAgent(
    { query: "unit" },
    "unit",
    new AbortController().signal,
    vi.fn(),
  );
  expect(response.status).toBe("partial");
  expect(response.results[0].image_id).toBe(id);
  expect(response.warnings).toContain("LLM_RATE_LIMITED");
});

test("fatal Agent errors still reject the stream", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response('event: error\ndata: {"code":"AGENT_BUSY"}\n\n', {
        headers: { "content-type": "text/event-stream" },
      }),
    ),
  );
  await expect(
    searchAgent(
      { query: "unit" },
      "unit",
      new AbortController().signal,
      vi.fn(),
    ),
  ).rejects.toThrow("AGENT_BUSY");
});
