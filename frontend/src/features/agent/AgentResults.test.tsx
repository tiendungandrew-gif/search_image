import { render, screen } from "@testing-library/react";
import { AgentResults } from "./AgentResults";

test("empty dataset displays no fabricated cards or steps", () => {
  render(
    <AgentResults
      loading={false}
      token="unit"
      progress={[]}
      response={{
        query_id: "unit",
        status: "insufficient_evidence",
        query_success: false,
        dataset_status: "empty_dataset",
        results: [],
        steps: [],
        latency_ms: 1,
        logical_hops: 0,
        tool_calls: 0,
        warnings: ["EMPTY_DATASET"],
        error_code: "EMPTY_DATASET",
        relationship_summary: null,
        rag: null,
      }}
    />,
  );
  expect(screen.getByText(/Chưa có dữ liệu ảnh/)).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText("Các bước đã thực hiện"),
  ).not.toBeInTheDocument();
});

test("verified relation sources are visible and unsafe URL schemes stay plain text", () => {
  render(
    <AgentResults
      loading={false}
      token="unit"
      progress={[]}
      response={{
        query_id: "unit",
        status: "insufficient_evidence",
        query_success: false,
        dataset_status: "available",
        results: [],
        steps: [],
        latency_ms: 1,
        logical_hops: 1,
        tool_calls: 2,
        warnings: [],
        error_code: null,
        relationship_summary: "Source-backed relation",
        rag: null,
        evidence: [
          {
            evidence_id: "one",
            source_ref: "https://www.nps.gov/wamo/index.htm",
            verified: true,
          },
          {
            evidence_id: "two",
            source_ref: "javascript:alert(1)",
            verified: true,
          },
        ],
      }}
    />,
  );
  expect(
    screen.getByRole("link", { name: "https://www.nps.gov/wamo/index.htm" }),
  ).toHaveAttribute("rel", "noopener noreferrer");
  expect(screen.getByText("javascript:alert(1)")).not.toHaveAttribute("href");
});

test("provider quota is separate from missing relationship evidence", () => {
  render(
    <AgentResults
      loading={false}
      token="unit"
      progress={[]}
      response={{
        query_id: "quota",
        status: "failed",
        query_success: false,
        dataset_status: "available",
        results: [],
        steps: [],
        latency_ms: 1,
        logical_hops: 0,
        tool_calls: 0,
        warnings: ["LLM_RATE_LIMITED"],
        error_code: "LLM_RATE_LIMITED",
        relationship_summary: null,
        rag: null,
      }}
    />,
  );
  expect(
    screen.getByText(/Dịch vụ AI đang giới hạn tần suất/),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/Chưa tìm được ảnh có đủ bằng chứng/),
  ).not.toBeInTheDocument();
});
