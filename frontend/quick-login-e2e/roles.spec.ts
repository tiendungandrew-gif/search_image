import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("quick Admin/User · real sessions, role landing pages, scoped search and logout", async ({
  page,
  context,
}, info) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Đăng nhập nhanh", exact: true }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: `../docs/verification/quick_login/login-${info.project.name}.png`,
    fullPage: true,
  });
  for (const role of ["admin", "user"] as const) {
    await page
      .getByRole("button", {
        name: new RegExp(
          role === "admin" ? "Vào nhanh Admin" : "Vào nhanh User",
        ),
      })
      .click();
    await expect(
      page.getByRole("button", { name: "Đăng xuất", exact: true }),
    ).toBeVisible();
    const me = await page.request.get("/api/v1/auth/me");
    const account = (await me.json()).user;
    expect(account.role).toBe(role);
    expect(account.is_demo).toBe(true);
    expect(
      (await context.cookies()).some(
        (c) => c.name === "lens_session" && c.httpOnly,
      ),
    ).toBe(true);
    expect(me.status()).toBe(200);
    expect((await page.request.get("/api/v1/admin/users")).status()).toBe(
      role === "admin" ? 200 : 403,
    );
    if (role === "admin") {
      await expect(page).toHaveURL(/\/admin$/);
      await expect(
        page.getByRole("heading", { name: "Không gian quản trị", exact: true }),
      ).toBeVisible();
    } else {
      await expect(page).toHaveURL(/\/$/);
      await expect(
        page.getByRole("link", { name: "Quản trị", exact: true }),
      ).toHaveCount(0);
      await page.locator("#query").fill("a photograph");
      await page
        .getByRole("button", { name: "Tùy chọn tìm kiếm", exact: true })
        .click();
      await page.getByText("Tùy chọn kết quả", { exact: true }).click();
      await page.locator("#top-k").fill("3");
      await page.getByText("Tùy chọn kết quả", { exact: true }).click();
      await page
        .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
        .click();
      await expect(page.locator(".result-card")).toHaveCount(3);
      await expect(page.locator(".result-card img").first()).toBeVisible();
      const allowed = account.datasets.map((d: { key: string }) => d.key);
      const response = await page.request.get("/api/v1/auth/me");
      expect((await response.json()).user.datasets.length).toBe(allowed.length);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Đăng nhập nhanh", exact: true }),
    ).toBeVisible();
    expect((await page.request.get("/api/v1/system/workspace")).status()).toBe(
      401,
    );
  }
});
