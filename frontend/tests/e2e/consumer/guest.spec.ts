import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("guest: public Vietnamese search, private denial and image sign-in gate", async ({
  page,
}, info) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Đăng nhập", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Hình dung điều bạn thích. Để Synlens tìm thấy.",
    }),
  ).toBeVisible();
  await expect(page.locator(".result-card")).toHaveCount(10, {
    timeout: 15000,
  });
  await expect(page.locator(".guest-banner")).toBeVisible();
  await page.getByRole("link", { name: "Thử tìm ảnh ngay" }).click();
  await expect(page.locator("#query")).toBeFocused();
  expect(
    await page
      .locator(".guest-photo-cat")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(
    page.getByRole("button", { name: "Tạm dừng hoạt ảnh" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Tạm dừng hoạt ảnh" }).click();
  expect(
    await page
      .locator(".guest-photo-cat")
      .evaluate((el) => getComputedStyle(el).animationPlayState),
  ).toBe("paused");
  await page.getByRole("button", { name: "Bật hoạt ảnh" }).click();
  expect(
    await page
      .locator(".guest-photo-cat")
      .evaluate((el) => getComputedStyle(el).animationPlayState),
  ).toBe("running");
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/verification/guest_search/landing-${info.project.name}.png`,
    fullPage: false,
  });
  const workspace = await page.request.get("/api/v1/public/workspace");
  expect(workspace.status()).toBe(200);
  const scope = await workspace.json();
  expect(scope.public_datasets.map((d: { key: string }) => d.key)).toEqual([
    "scikit-image-v0.25.2",
  ]);
  expect(scope.dataset.images).toBe(10);
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(200);
  expect(
    (await (await page.request.get("/api/v1/auth/me")).json()).user,
  ).toBeNull();
  expect((await page.request.get("/api/v1/admin/users")).status()).toBe(401);
  for (const query of ["con meo", "a cat"]) {
    await page.locator("#query").fill(query);
    const pending = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        new URL(r.url()).pathname === "/api/v1/search",
    );
    await page
      .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
      .click();
    const response = await pending;
    expect(response.status(), await response.text()).toBe(200);
    const data = await response.json();
    expect(data.results.length).toBeGreaterThan(0);
    expect(
      data.results.every(
        (r: { metadata: { source_dataset: string } }) =>
          r.metadata.source_dataset === "scikit-image-v0.25.2",
      ),
    ).toBe(true);
    // The top image is the sample cat (451 x 300), not an arbitrary HTTP 200.
    expect(data.results[0].metadata.width).toBe(451);
    expect(data.results[0].metadata.height).toBe(300);
    await expect(
      page.locator(".result-card").first().locator(".result-media"),
    ).toHaveAttribute("data-ready", "true");
  }
  const csrfCookies = (await page.context().cookies()).filter((cookie) =>
    cookie.name.includes("lens_session"),
  );
  expect(csrfCookies).toEqual([]);
  await page
    .getByRole("button", { name: "Phóng to ảnh hạng 1", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".result-media")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
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
  for (const card of await page.locator(".result-card").all()) {
    await card.scrollIntoViewIfNeeded();
    await expect(card.locator(".result-media")).toHaveAttribute(
      "data-ready",
      "true",
      { timeout: 10000 },
    );
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/verification/guest_search/guest-${info.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Tìm bằng ảnh", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/login");
});
