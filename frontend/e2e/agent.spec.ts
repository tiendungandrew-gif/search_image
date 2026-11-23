import { expect, test } from "@playwright/test";

test("public landmark workflow shows real photos and relationship sources", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_AGENT_PUBLIC_DATA !== "1",
    "Requires verified public NPS knowledge",
  );
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN ?? "");
  await page.locator("#mode").selectOption("agent");
  await page
    .locator("#query")
    .fill("Find landmarks in the city where Washington Monument is located");
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  await expect(page.getByTestId("agent-status")).toContainText("Đã hoàn tất", {
    timeout: 20000,
  });
  await expect(page.locator(".result-card")).toHaveCount(3);
  await expect(
    page.getByLabel("Các bước đã thực hiện").locator("li"),
  ).toHaveCount(4);
  await page.getByText("Nguồn quan hệ", { exact: true }).click();
  await expect(
    page.getByRole("link", { name: "https://www.nps.gov/wamo/index.htm" }),
  ).toBeVisible();
  await expect(
    page.getByText("Quan hệ có nguồn trong dữ liệu:", { exact: false }),
  ).toContainText("Washington, D.C.");
});

test("mocked optional RAG quota warning preserves real public images in SSE UI", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_AGENT_PUBLIC_DATA !== "1",
    "Requires verified NPS image receipts",
  );
  const token = process.env.API_TOKEN ?? "";
  const r = await page.request.post("/api/v1/search/agent", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      query: "Find landmarks in the city where Washington Monument is located",
      top_k: 10,
    },
  });
  expect(r.status()).toBe(200);
  const value = await r.json();
  expect(value.results).toHaveLength(3);
  value.status = "partial";
  value.query_success = false;
  value.warnings = ["LLM_RATE_LIMITED"];
  await page.route("**/search/agent/stream", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body:
        'event: error\ndata: {"code":"LLM_RATE_LIMITED","retrieval_preserved":true}\n\n' +
        `event: agent_partial\ndata: ${JSON.stringify(value)}\n\n`,
    }),
  );
  await page.goto("/");
  await page.locator("#search-token").fill(token);
  await page.locator("#mode").selectOption("agent");
  await page.locator("#query").fill("public quota UI test");
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  await expect(page.getByTestId("agent-status")).toContainText(
    "Kết quả một phần",
  );
  await expect(
    page.getByText(/Dịch vụ AI đang giới hạn tần suất/),
  ).toBeVisible();
  await expect(page.locator(".result-card")).toHaveCount(3);
  await expect(page.locator(".result-card img").first()).toBeVisible();
});

test("agent missing relation uses live API and does not fabricate landmark images", async ({
  page,
}) => {
  test.skip(process.env.RUN_AGENT_E2E !== "1", "Requires enabled Agent API");
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN ?? "");
  await page.locator("#mode").selectOption("agent");
  await page
    .locator("#query")
    .fill("Find landmarks in the city where Hoan Kiem Lake is located");
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/search/agent/stream"),
  );
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  expect((await pending).status()).toBe(200);
  await expect(page.getByTestId("agent-status")).toContainText(
    "Chưa đủ bằng chứng",
    { timeout: 20000 },
  );
  await expect(page.locator(".result-card")).toHaveCount(0);
  await expect(page.getByLabel("Các bước đã thực hiện")).toContainText(
    "Tra cứu thực thể",
  );
  await expect(page.getByText("Quan hệ có nguồn trong dữ liệu:")).toHaveCount(
    0,
  );
});

test("agent returns live indexed images and real optional Gemini citations", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_AGENT_E2E !== "1",
    "Requires Agent/RAG and real indexed captions",
  );
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN ?? "");
  await page.locator("#mode").selectOption("agent");
  await page.locator("#query").fill("a dog outdoors");
  await page.locator("#top-k").fill("1");
  await page.getByLabel("Giải thích sau khi tìm ảnh").check();
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  await expect(page.getByTestId("agent-status")).toContainText("Đã hoàn tất", {
    timeout: 25000,
  });
  await expect(page.locator(".result-card")).toHaveCount(1);
  const citation = page
    .getByTestId("agent-results")
    .locator("a[href^='#image-']")
    .first();
  await expect(citation).toBeVisible();
  await citation.click();
  await expect(page.locator(".result-card img")).toBeVisible();
});

test("empty-dataset Agent UI is exercised with an explicitly mocked SSE response", async ({
  page,
}) => {
  test.skip(process.env.RUN_AGENT_E2E !== "1", "Requires Agent UI");
  await page.route("**/search/agent/stream", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body:
        "event: planning_started\ndata: {}\n\nevent: agent_partial\ndata: " +
        JSON.stringify({
          query_id: "ui-fixture",
          status: "insufficient_evidence",
          query_success: false,
          dataset_status: "empty_dataset",
          results: [],
          steps: [],
          latency_ms: 0,
          logical_hops: 0,
          tool_calls: 0,
          warnings: ["EMPTY_DATASET"],
          error_code: "EMPTY_DATASET",
          relationship_summary: null,
          rag: null,
        }) +
        "\n\n",
    }),
  );
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN ?? "");
  await page.locator("#mode").selectOption("agent");
  await page.locator("#query").fill("a fictional fixture query");
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  await expect(
    page.getByText("Chưa có dữ liệu ảnh để tìm kiếm.", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".result-card")).toHaveCount(0);
});
