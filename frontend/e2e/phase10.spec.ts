import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function connect(page: Page) {
  test.skip(!process.env.API_TOKEN, "Cần backend và API_TOKEN thật");
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN!);
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
}
async function search(page: Page) {
  await page.locator("#query").fill("a cup of coffee");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.locator(".result-card")).toHaveCount(10);
}

test("REAL · dataset, gallery, metadata dialog and keyboard focus", async ({
  page,
}, info) => {
  await connect(page);
  await expect(page.getByTestId("dataset-status")).toContainText("513");
  await search(page);
  const opener = page.getByRole("button", {
    name: "Xem chi tiết ảnh hạng 1",
    exact: true,
  });
  const current = page.waitForResponse((reply) =>
    /\/images\/[a-f0-9-]+$/.test(new URL(reply.url()).pathname),
  );
  await opener.click();
  expect((await current).status()).toBe(200);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Mã ảnh");
  await expect(dialog.locator("img")).toBeVisible();
  await expect
    .poll(() =>
      dialog
        .locator("img")
        .evaluate((node) => (node as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(0);
  await page.keyboard.press("ArrowRight");
  await expect(dialog).toContainText("Ảnh 2 / 10");
  await page.keyboard.press("Tab");
  expect(
    await page.evaluate(() => !!document.activeElement?.closest("dialog")),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(opener).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: info.outputPath("phase10-gallery.png"),
    fullPage: true,
  });
});

test("REAL · metadata filters distinguish no matches from an empty dataset", async ({
  page,
}) => {
  await connect(page);
  await page.getByText("Tùy chọn tìm kiếm nâng cao", { exact: true }).click();
  await page
    .locator("#filter-source")
    .fill("phase10-intentionally-absent-source");
  await page.locator("#query").fill("coffee");
  const pending = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/v1/search") &&
      reply.request().method() === "POST",
  );
  await page.locator("#query").press("Enter");
  const reply = await pending;
  expect(reply.status()).toBe(200);
  expect(reply.request().postDataJSON().filters.source_dataset).toBe(
    "phase10-intentionally-absent-source",
  );
  await expect(
    page.getByText("Không tìm thấy ảnh phù hợp.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  await expect(page.locator(".result-card")).toHaveCount(0);
});

test("REAL · benchmark navigation uses authenticated aggregate API", async ({
  page,
}) => {
  await connect(page);
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(page).toHaveURL(/\/evaluation$/);
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("table")).toContainText(
    "20261106T151820_benchmark_5b73a0ef43",
  );
  await expect(page.getByRole("table")).toContainText("136.61");
  await page.goBack();
  await expect(page.locator("#query")).toBeVisible();
  await expect(page.locator("#search-token")).toHaveValue(
    process.env.API_TOKEN!,
  );
});

test("REAL · accessibility checks on search, dialog, dark theme and evaluation", async ({
  page,
}, info) => {
  await connect(page);
  await search(page);
  const snapshots: { view: string; violations: unknown[] }[] = [];
  async function audit(view: string) {
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    snapshots.push({ view, violations: result.violations });
    expect(
      result.violations.map((item) => ({
        id: item.id,
        targets: item.nodes.map((node) => node.target),
      })),
    ).toEqual([]);
  }
  await audit("search-light");
  await page
    .getByRole("button", { name: "Xem chi tiết ảnh hạng 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await audit("dialog");
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Giao diện tối", exact: true })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await audit("search-dark");
  const stored = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }));
  expect(stored).toEqual({ local: ["lens.theme"], session: [] });
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await audit("evaluation-dark");
  await info.attach("axe-results", {
    body: JSON.stringify(snapshots),
    contentType: "application/json",
  });
});

test("MOCK · empty dataset, disabled features and a later import refresh", async ({
  page,
}) => {
  let ready = false;
  const disabled = {
    text_search: false,
    image_search: false,
    multimodal: false,
    multi_intent: false,
    rerank: false,
    explanations: false,
    agent: false,
  };
  await page.route("**/api/v1/system/workspace", async (route) =>
    route.fulfill({
      json: {
        dataset: {
          state: ready ? "ready" : "empty_dataset",
          images: ready ? 3 : 0,
          available_images: ready ? 3 : 0,
          indexed_images: ready ? 3 : 0,
          vectors: ready ? 3 : 0,
          index_id: null,
          index_status: ready ? "ready" : "absent",
          generation: ready ? 1 : null,
        },
        dependencies: {
          postgresql: "healthy",
          qdrant: "healthy",
          minio: "healthy",
        },
        capabilities: { ...disabled, text_search: ready, image_search: ready },
        rag: { enabled: false, configured: false, streaming: false },
        agent: { enabled: false, llm_planning: false },
        limits: { top_k: 50, image_bytes: 20971520 },
      },
    }),
  );
  await page.goto("/");
  await page.locator("#search-token").fill("explicit-test-token");
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Chưa có dữ liệu ảnh",
  );
  await expect(page.locator('option[value="agent"]')).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".result-card")).toHaveCount(0);
  ready = true;
  await page
    .getByRole("button", { name: "Làm mới dataset", exact: true })
    .click();
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  await page.locator("#query").fill("coffee");
  await expect(
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
  ).toBeEnabled();
});

test("MOCK · backend unavailable is never reported as an empty dataset", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (route) => route.abort("failed"));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Chưa kết nối được API");
  await expect(
    page.getByText("Chưa kết nối API", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Chưa có dữ liệu ảnh.", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Nhìn vào",
  );
});
