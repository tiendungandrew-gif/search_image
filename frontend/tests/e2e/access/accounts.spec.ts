import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import path from "node:path";
import { randomBytes } from "node:crypto";
const credentials = JSON.parse(
  readFileSync(
    process.env.ACCESS_LOGIN_FILE ??
      path.resolve(
        import.meta.dirname,
        "../../../../.cache/auth/qa-admin-login.json",
      ),
    "utf8",
  ),
) as { username: string; password: string };
async function login(page: Page, username: string, password: string) {
  await page.goto("/");
  await page.getByLabel("Tên đăng nhập", { exact: true }).fill(username);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
}
async function accessible(page: Page) {
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
}
test("REAL SERVICES · account creation, grants, scoped search and admin separation", async ({
  page,
  browser,
}, info) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
  await accessible(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/verification/access_control/login-${info.project.name}.png`,
    fullPage: true,
  });
  await login(page, credentials.username, credentials.password);
  await page.getByRole("link", { name: "Quản trị", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Không gian quản trị" }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("link", { name: "Tài khoản", exact: true }).click();
  await page.getByText("Tạo tài khoản mới", { exact: true }).click();
  const form = page.locator("details.admin-card form");
  const username = "browser_" + randomBytes(6).toString("hex");
  const password = randomBytes(20).toString("base64url");
  await form.getByLabel("Tên đăng nhập", { exact: true }).fill(username);
  await form
    .getByLabel("Tên hiển thị", { exact: true })
    .fill("Thành viên kiểm thử");
  await form
    .getByLabel("Mật khẩu (ít nhất 12 ký tự)", { exact: true })
    .fill(password);
  await form
    .getByRole("button", { name: "Tạo tài khoản", exact: true })
    .click();
  await expect(
    page.getByText("Đã tạo tài khoản. Hãy cấp thư viện cho thành viên mới."),
  ).toBeVisible();
  const editor = page
    .locator("details.user-editor")
    .filter({ hasText: "@" + username });
  await editor.locator("summary").click();
  const checkboxes = editor.locator("fieldset input[type=checkbox]");
  if (await checkboxes.count()) {
    await checkboxes.first().check();
    await editor.getByRole("button", { name: "Lưu quyền thư viện" }).click();
    await expect(page.getByText("Đã cập nhật quyền thư viện.")).toBeVisible();
  }
  await accessible(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/verification/access_control/admin-${info.project.name}.png`,
    fullPage: true,
  });
  const userContext = await browser.newContext({
    baseURL: process.env.ACCESS_BASE_URL ?? "http://127.0.0.1:5175",
    viewport: info.project.use.viewport,
  });
  const user = await userContext.newPage();
  try {
    await login(user, username, password);
    await expect(
      user.getByRole("link", { name: "Quản trị", exact: true }),
    ).toHaveCount(0);
    await expect(user.locator("#search-token")).toHaveCount(0);
    await expect(
      user.getByText("Kiểm tra hạ tầng", { exact: true }),
    ).toHaveCount(0);
    const searchButton = user.getByRole("button", {
      name: "Tìm kiếm ảnh",
      exact: true,
    });
    if (process.env.ACCESS_INDEXED === "1") {
      await user.locator("#query").fill("colored geometric shapes");
      await expect(searchButton).toBeEnabled();
      await searchButton.click();
      await expect(user.locator(".result-card").first()).toBeVisible();
      await expect(user.locator(".result-card img").first()).toBeVisible();
    }
    await accessible(user);
    await user.evaluate(() => window.scrollTo(0, 0));
    await user.screenshot({
      path: `../docs/verification/access_control/search-${info.project.name}.png`,
      fullPage: true,
    });
    expect((await user.request.get("/api/v1/admin/users")).status()).toBe(403);
    await user.goto("/admin");
    await expect(
      user.getByRole("heading", { name: "Bạn không có quyền quản trị" }),
    ).toBeVisible();
    await user.getByRole("button", { name: /^(Giao diện tối|Tối)$/ }).click();
    await expect(user.locator("html")).toHaveAttribute("data-theme", "dark");
    await accessible(user);
    await user.getByRole("button", { name: "Đăng xuất" }).click();
    await expect(
      user.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
    ).toBeVisible();
    await accessible(user);
    expect((await user.request.get("/api/v1/system/workspace")).status()).toBe(
      401,
    );
  } finally {
    await userContext.close();
  }
  await page.getByRole("link", { name: "Thư viện", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hình ảnh", exact: true }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("link", { name: "Nhật ký", exact: true }).click();
  await expect(page.getByRole("table")).toContainText("user.created");
});
