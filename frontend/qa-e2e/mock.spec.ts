import { expect, test } from "@playwright/test";
import { capabilities, id, image, png, search, workspace } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/auth/me"))
      return route.fulfill({ json: { user: null, legacy_enabled: true } });
    if (url.pathname.endsWith("/health"))
      return route.fulfill({
        json: {
          status: "ok",
          check: "live",
          capabilities,
          worker: { state: "unknown" },
        },
      });
    if (url.pathname.endsWith("/system/workspace"))
      return route.fulfill({ json: workspace });
    if (url.pathname.includes("/content"))
      return route.fulfill({ contentType: "image/png", body: png });
    if (url.pathname.endsWith("/search"))
      return route.fulfill({ json: search });
    return route.fulfill({
      status: 503,
      json: {
        error: {
          code: "TEST_UNAVAILABLE",
          message: "Explicit mock unavailable",
          request_id: id,
          retryable: true,
          details: [],
        },
      },
    });
  });
  await page.goto("/operator");
  await page.locator("#search-token").fill("mock-only-not-a-real-key");
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
});

test("MOCK · cancellation discards a late response and retry stays functional", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/search", async (route) => {
    await gate;
    await route.fulfill({ json: search }).catch(() => {});
  });
  await page.locator("#query").fill("cancel fixture");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await page.getByRole("button", { name: "Hủy tìm kiếm", exact: true }).click();
  release();
  await expect(page.locator(".results-section")).toHaveAttribute(
    "data-state",
    "CANCELLED",
  );
  await expect(page.locator(".result-card")).toHaveCount(0);
  await page.unroute("**/api/v1/search");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.locator(".result-card")).toHaveCount(1);
});

test("MOCK · recoverable RAG SSE failure preserves final state and image cards", async ({
  page,
}) => {
  await page.locator("#query").fill("fixture metadata");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.locator(".result-card")).toHaveCount(1);
  await page.route("**/rag/explain/stream", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body:
        'event: error\ndata: {"code":"LLM_TIMEOUT","retrieval_preserved":true}\n\n' +
        `event: generation_completed\ndata: ${JSON.stringify({ rag: { answer: "Explicit mock generation unavailable; images retained.", grounding_status: "generation_unavailable", generated: false, error_code: "LLM_TIMEOUT", citations: [] } })}\n\n`,
    }),
  );
  await page
    .getByRole("button", { name: "Giải thích bằng AI", exact: true })
    .click();
  await expect(page.getByTestId("rag-answer")).toContainText("images retained");
  await expect(page.locator(".result-card")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Thử lại giải thích" }),
  ).toBeEnabled();
});

test("MOCK · metadata text is inert and foreign media is rejected", async ({
  page,
}) => {
  const title = '<img src=x onerror="window.__QA_XSS=1">';
  await page.route("**/api/v1/search", (route) =>
    route.fulfill({
      json: {
        ...search,
        results: [{ ...image, metadata: { ...image.metadata, title } }],
      },
    }),
  );
  await page.locator("#query").fill("xss fixture");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.getByText(title, { exact: false })).toBeVisible();
  expect(await page.evaluate(() => Object.hasOwn(window, "__QA_XSS"))).toBe(
    false,
  );
  await page.route("**/api/v1/search", (route) =>
    route.fulfill({
      json: {
        ...search,
        results: [{ ...image, thumbnail_url: "https://foreign.invalid/pixel" }],
      },
    }),
  );
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("không đúng định dạng");
  await expect(page.locator(".result-card")).toHaveCount(0);
});

test("MOCK · lazy module failure has a recoverable application fallback", async ({
  page,
}) => {
  await page.route("**/src/features/evaluation/EvaluationPage.tsx*", (route) =>
    route.abort("failed"),
  );
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Giao diện tạm thời");
  await expect(
    page.getByRole("button", { name: "Tải lại giao diện", exact: true }),
  ).toBeEnabled();
});
