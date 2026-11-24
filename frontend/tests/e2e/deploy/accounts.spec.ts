import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
const credentials = JSON.parse(
  readFileSync(process.env.DEPLOY_LOGIN_FILE!, "utf8"),
) as { username: string; password: string };
test("deployment · private login, search and admin workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
  await page
    .getByLabel("Tên đăng nhập", { exact: true })
    .fill(credentials.username);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Thư viện của bạn" }),
  ).toBeVisible();
  await expect(page.locator("#search-token")).toHaveCount(0);
  if (process.env.DEPLOY_INDEXED === "1") {
    await page.locator("#query").fill("colored geometric shapes");
    await page
      .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
      .click();
    await expect(page.locator(".result-card img").first()).toBeVisible();
  }
  await page.getByRole("link", { name: "Quản trị", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Không gian quản trị" }),
  ).toBeVisible();
  await expect(page.getByTestId("dataset-status")).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
});
