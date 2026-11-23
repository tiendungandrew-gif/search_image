import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { SearchResponse } from "../../types/api";
import { ExplanationPanel } from "./ExplanationPanel";

const imageId = "785c1ac8-6017-4c02-84d4-5d4f67ef4142";
const results = {
  index_id: "6c3a8404-2971-46bf-ac9c-5c09bdec42b5",
  results: [{ image_id: imageId }],
} as SearchResponse;
function response(error: string | null = null) {
  return new Response(
    JSON.stringify({
      rag: {
        answer: error
          ? "Kết quả ảnh vẫn có sẵn."
          : "Theo metadata đã lưu, ảnh có định dạng image/png.",
        grounding_status: error ? "generation_unavailable" : "supported",
        generated: !error,
        error_code: error,
        citations: error
          ? []
          : [
              {
                image_id: imageId,
                evidence_field: "media_type",
                quote: "image/png",
              },
            ],
      },
    }),
  );
}

test("provider timeout offers an explicit retry without automatic repeated calls", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(response("LLM_TIMEOUT"))
    .mockResolvedValueOnce(response());
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(
    <ExplanationPanel results={results} token="unit-token" query="coffee" />,
  );
  await user.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  expect(await screen.findByText(/LLM_TIMEOUT/)).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "Thử lại giải thích" }));
  expect(await screen.findByText(/Theo metadata/)).toBeInTheDocument();
  expect(screen.getByRole("link")).toHaveAttribute("href", `#image-${imageId}`);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(JSON.parse(fetch.mock.calls[1][1].body).image_ids).toEqual([imageId]);
});

test("cancel closes the request and a late aborted result cannot replace the retry", async () => {
  let firstResolve: (value: Response) => void = () => {};
  const fetch = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          firstResolve = resolve;
        }),
    )
    .mockResolvedValueOnce(response());
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(
    <ExplanationPanel results={results} token="unit-token" query="coffee" />,
  );
  await user.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  await user.click(screen.getByRole("button", { name: "Dừng giải thích" }));
  expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  await user.click(screen.getByRole("button", { name: "Thử lại giải thích" }));
  expect(await screen.findByText(/Theo metadata/)).toBeInTheDocument();
  // A transport resolving late after cancellation must not replace the newer answer.
  await act(async () => firstResolve(response("LLM_TIMEOUT")));
  expect(screen.queryByText(/LLM_TIMEOUT/)).not.toBeInTheDocument();
  expect(screen.getByText(/Theo metadata/)).toBeInTheDocument();
});

test("an unknown image citation is rejected and retry is available", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          rag: {
            answer: "bad reference",
            citations: [{ image_id: "unknown", quote: "invented" }],
          },
        }),
      ),
    ),
  );
  render(
    <ExplanationPanel results={results} token="unit-token" query="coffee" />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  await waitFor(() =>
    expect(screen.getByRole("alert")).toHaveTextContent("không đúng định dạng"),
  );
  expect(
    screen.getByRole("button", { name: "Thử lại giải thích" }),
  ).toBeEnabled();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

test("RAG SSE ignores unverified tokens and only displays the validated terminal answer", async () => {
  const terminal = await response().json();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          "event: generation_started\ndata: {}\n\n" +
            'event: token\ndata: {"text":"UNVERIFIED_PRIVATE_TEXT"}\n\n' +
            `event: generation_completed\ndata: ${JSON.stringify(terminal)}\n\n`,
          { headers: { "content-type": "text/event-stream" } },
        ),
      ),
  );
  render(
    <ExplanationPanel
      results={results}
      token="unit"
      query="coffee"
      streaming
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  expect(await screen.findByText(/Theo metadata/)).toBeInTheDocument();
  expect(screen.queryByText(/UNVERIFIED_PRIVATE_TEXT/)).not.toBeInTheDocument();
});

test("an incomplete RAG stream shows an error without inventing an answer", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response("event: generation_started\ndata: {}\n\n", {
        headers: { "content-type": "text/event-stream" },
      }),
    ),
  );
  render(
    <ExplanationPanel
      results={results}
      token="unit"
      query="coffee"
      streaming
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "chưa có kết quả xác nhận",
  );
  expect(screen.queryByTestId("rag-answer")).not.toBeInTheDocument();
});

test("recoverable RAG stream errors wait for the validated terminal unavailable result", async () => {
  const terminal = await response("LLM_TIMEOUT").json();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          'event: error\ndata: {"code":"LLM_TIMEOUT","retrieval_preserved":true}\n\n' +
            `event: generation_completed\ndata: ${JSON.stringify(terminal)}\n\n`,
          { headers: { "content-type": "text/event-stream" } },
        ),
      ),
  );
  render(
    <ExplanationPanel
      results={results}
      token="unit"
      query="coffee"
      streaming
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Giải thích bằng AI" }));
  expect(await screen.findByTestId("rag-answer")).toHaveTextContent(
    "Kết quả ảnh vẫn có sẵn.",
  );
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Thử lại giải thích" }),
  ).toBeEnabled();
});
