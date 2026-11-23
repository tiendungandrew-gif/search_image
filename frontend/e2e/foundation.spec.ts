import { test, expect } from "@playwright/test";
import path from "node:path";

async function authenticate(page: import("@playwright/test").Page) {
  const token = process.env.API_TOKEN;
  test.skip(!token, "Cần API_TOKEN cho actual backend");
  await page.goto("/");
  await expect(page.getByText("API đang hoạt động")).toBeVisible();
  await page.getByLabel("Token truy cập", { exact: true }).fill(token!);
}

test("text search thật trả ảnh có metadata, preview và không tràn viewport", async ({
  page,
}, info) => {
  await authenticate(page);
  await page.getByLabel("Bạn đang tìm hình ảnh nào?").fill("a cup of coffee");
  const reply = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/search") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  const response = await reply;
  expect(response.status()).toBe(200);
  await expect(page.locator(".result-card")).toHaveCount(10);
  const preview = page.locator(".result-card img").first();
  await expect(preview).toBeVisible();
  await expect
    .poll(() =>
      preview.evaluate((image) => (image as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
  ).toBe(0);
  await page.screenshot({
    path: info.outputPath("search.png"),
    fullPage: true,
  });
});

test("image search thật không ingest query ảnh vào corpus", async ({
  page,
}) => {
  await authenticate(page);
  const mutations: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && !request.url().includes("/search"))
      mutations.push(request.url());
  });
  await page.getByLabel("Phương thức").selectOption("image");
  await page
    .locator("#reference-image")
    .setInputFiles(
      path.resolve(import.meta.dirname, "../../datasets/sample/coffee.png"),
    );
  await expect(page.getByAltText("Ảnh tham chiếu xem trước")).toBeVisible();
  const reply = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/search/multimodal"),
  );
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  expect((await reply).status()).toBe(200);
  await expect(page.locator(".result-card")).toHaveCount(10);
  expect(mutations).toEqual([]);
});

test("invalid token báo lỗi; advanced mode đã bật", async ({ page }) => {
  await page.goto("/");
  await page
    .getByLabel("Token truy cập", { exact: true })
    .fill("intentionally-invalid-token");
  await page.getByLabel("Bạn đang tìm hình ảnh nào?").fill("coffee");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Bearer token");
  expect(await page.locator('option[value="multimodal"]').isDisabled()).toBe(
    false,
  );
});

test("multi-intent AND OR và tiếng Việt có evidence chưa xác minh", async ({
  page,
}) => {
  await authenticate(page);
  await page.getByLabel("Phương thức").selectOption("multi_intent");
  await page.getByText("Tùy chọn tìm kiếm nâng cao", { exact: true }).click();
  await page.getByLabel("Xếp hạng lại theo điều kiện").check();
  for (const query of [
    "coffee and a brown cat",
    "coffee or a brown cat",
    "cà phê và mèo màu nâu",
  ]) {
    await page.getByLabel("Bạn đang tìm hình ảnh nào?").fill(query);
    const reply = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/search") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
      .click();
    const response = await reply;
    expect(response.status()).toBe(200);
    const value = await response.json();
    expect(value.effective_settings.rerank_applied).toBe(true);
    expect(value.query_analysis.query_type).toBe("MULTI_INTENT");
    await expect(page.locator(".result-card")).toHaveCount(10);
    await expect(page.locator(".constraint-evidence").first()).toContainText(
      "Chưa xác minh",
    );
  }
});

test("combined text image chạy cả RRF và weighted score", async ({
  page,
}, info) => {
  await authenticate(page);
  await page.getByLabel("Phương thức").selectOption("multimodal");
  await page.getByLabel("Bạn đang tìm hình ảnh nào?").fill("a cup of coffee");
  await page
    .locator("#reference-image")
    .setInputFiles(
      path.resolve(import.meta.dirname, "../../datasets/sample/coffee.png"),
    );
  await page.getByText("Tùy chọn tìm kiếm nâng cao", { exact: true }).click();
  for (const method of ["rrf", "weighted_score"]) {
    await page
      .getByLabel("Kết hợp kết quả", { exact: true })
      .selectOption(method);
    const reply = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/search/multimodal"),
    );
    await page
      .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
      .click();
    const response = await reply;
    expect(response.status()).toBe(200);
    const value = await response.json();
    expect(value.search_mode).toBe("multimodal");
    expect(value.effective_settings.fusion_version).toBe(method + "-v1");
    expect(
      value.results[0].contributing_branches.map(
        (b: { branch: string }) => b.branch,
      ),
    ).toEqual(expect.arrayContaining(["whole", "image"]));
    await expect(page.locator(".result-card")).toHaveCount(10);
    await expect(page.locator(".result-card img")).toHaveCount(10);
    // Native lazy images ngoài viewport chưa decode; kiểm tra theo thao tác cuộn thật.
    for (const card of await page.locator(".result-card").all()) {
      await card.scrollIntoViewIfNeeded();
      const image = card.locator("img");
      await expect
        .poll(() =>
          image.evaluate((node) => (node as HTMLImageElement).naturalWidth),
        )
        .toBeGreaterThan(0);
    }
    await expect
      .poll(() =>
        page
          .locator(".result-card img")
          .evaluateAll((images) =>
            images.every(
              (image) => (image as HTMLImageElement).naturalWidth > 0,
            ),
          ),
      )
      .toBe(true);
  }
  await expect(
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
  ).toBeEnabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: info.outputPath("advanced-search.png"),
    fullPage: true,
  });
});

test("unsupported relational query báo rõ không có multi-hop", async ({
  page,
}) => {
  await authenticate(page);
  await page
    .getByLabel("Bạn đang tìm hình ảnh nào?")
    .fill("Find landmarks in the city where Hoan Kiem Lake is located");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("multi-hop");
  await expect(page.locator(".result-card")).toHaveCount(0);
});
