import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const indexed = process.env.DEPLOY_INDEXED === "1";
test("DEPLOYMENT · static frontend, API, deep link and empty benchmark", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.DEPLOY_READ_TOKEN!);
  await expect(
    page.getByText("API đang hoạt động", { exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("dataset-status")).toContainText(
    indexed ? "Dataset sẵn sàng" : "Chưa có dữ liệu ảnh",
  );
  if (!indexed) {
    await page.locator("#query").fill("colored shapes");
    await expect(
      page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
    ).toBeDisabled();
    await expect(page.locator(".result-card")).toHaveCount(0);
  }
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(
    page.getByText(
      /Nguồn benchmark chưa được cấu hình|Chưa có kết quả benchmark/,
    ),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.locator("#evaluation-heading"),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("DEPLOYMENT / SYNTHETIC · search, private media, details and mobile layout", async ({
  page,
}) => {
  test.skip(!indexed, "Separate empty profile; no synthetic images imported");
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.DEPLOY_READ_TOKEN!);
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  await page.locator("#top-k").fill("3");
  await page.locator("#query").fill("colored geometric shapes");
  const reply = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/v1/search"),
  );
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  expect((await reply).status()).toBe(200);
  await expect(page.locator(".result-card")).toHaveCount(3);
  await expect(page.locator(".result-card img").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Xem chi tiết ảnh hạng 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("phase12_synthetic@v1");
  await page.keyboard.press("Escape");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(
    page.getByRole("button", { name: "Giải thích bằng AI" }),
  ).toHaveCount(0);
});
