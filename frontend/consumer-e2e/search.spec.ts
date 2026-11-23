import { expect, test, type Page, type Response } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";

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
async function openSettings(page: Page) {
  const toggle = page.getByRole("button", {
    name: "Tùy chọn tìm kiếm",
    exact: true,
  });
  if ((await toggle.getAttribute("aria-expanded")) !== "true")
    await toggle.click();
}
async function search(page: Page) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        /\/api\/v1\/search(?:\/multimodal)?$/.test(new URL(r.url()).pathname),
      { timeout: 10000 },
    ),
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click(),
  ]);
  expect(response.status(), await response.text()).toBe(200);
  await expect(page.locator(".result-card")).toHaveCount(3);
  await expect(page.locator(".result-card img").first()).toBeVisible();
  await expect(page.locator("#results-heading")).toBeFocused();
  return response;
}
async function revealGallery(page: Page) {
  for (const card of await page.locator(".result-card").all()) {
    await card.scrollIntoViewIfNeeded();
    await expect(card.locator("img")).toBeVisible({ timeout: 10000 });
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}
function options(response: Response) {
  return response.request().postDataJSON() as {
    mode: string;
    filters: { source_dataset?: string };
  };
}

test("consumer gallery · real scoped search, topic selection and accessible details", async ({
  page,
}, info) => {
  await page.goto("/login");
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
  const quickUser = page.getByRole("button", { name: /Vào nhanh User/ });
  const retryAuth = page.getByRole("button", {
    name: "Kiểm tra lại kết nối",
    exact: true,
  });
  await expect(quickUser.or(retryAuth).first()).toBeVisible({ timeout: 15000 });
  if (await retryAuth.isVisible()) await retryAuth.click();
  await expect(quickUser).toBeVisible({ timeout: 15000 });
  await accessible(page);
  await page.screenshot({
    path: `../docs/verification/consumer_ui/login-${info.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("link", { name: "Synlens trang chủ" }).focus();
  await page.keyboard.press("Tab");
  await expect(page.locator("#login-username")).toBeFocused();
  await page.getByRole("button", { name: /Vào nhanh User/ }).focus();
  const discoveryResponse = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      new URL(r.url()).pathname === "/api/v1/search" &&
      r.request().postDataJSON()?.text === "a photograph",
  );
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Một ý tưởng, nhiều góc nhìn." }),
  ).toBeVisible();
  await expect(page.locator(".guest-banner")).toHaveCount(0);
  await openSettings(page);
  await expect(
    page.getByRole("button", { name: "Mô tả", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  expect((await page.request.get("/api/v1/admin/users")).status()).toBe(403);
  const discovery = await discoveryResponse;
  expect(discovery.status()).toBe(200);
  const account = (await (await page.request.get("/api/v1/auth/me")).json())
    .user;
  const allowed = account.datasets.map((d: { key: string }) => d.key);
  expect(
    (await discovery.json()).results.every(
      (r: { metadata: { source_dataset: string } }) =>
        allowed.includes(r.metadata.source_dataset),
    ),
  ).toBe(true);
  await expect(page.locator(".result-card")).toHaveCount(12);
  await page.locator(".result-card").first().scrollIntoViewIfNeeded();
  await expect(page.locator(".result-card img").first()).toBeVisible();
  const initialOrder = await page
    .locator(".result-card")
    .evaluateAll((cards) => cards.map((c) => c.id));
  const initialCardWidth = (await page
    .locator(".result-card")
    .first()
    .boundingBox())!.width;
  await page.getByRole("button", { name: "Lưới gọn", exact: true }).click();
  await expect
    .poll(
      async () =>
        (await page.locator(".result-card").first().boundingBox())!.width,
    )
    .toBeLessThan(initialCardWidth);
  await expect(
    page.getByRole("button", { name: "Lưới gọn", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    await page
      .locator(".result-card")
      .evaluateAll((cards) => cards.map((c) => c.id)),
  ).toEqual(initialOrder);
  await page.getByRole("button", { name: "Lưới lớn", exact: true }).click();

  await page
    .getByRole("button", { name: "Tùy chọn tìm kiếm", exact: true })
    .click();
  const query = page.getByRole("combobox", {
    name: "Bạn đang tìm hình ảnh nào?",
  });
  await expect(
    page
      .locator(".app-header")
      .getByRole("combobox", { name: "Bạn đang tìm hình ảnh nào?" }),
  ).toBeVisible();
  let requests = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      new URL(request.url()).pathname.startsWith("/api/v1/search")
    )
      requests++;
  });
  await query.fill("ho");
  await expect(page.getByRole("listbox")).toBeVisible();
  await page.screenshot({
    path: `../docs/verification/consumer_ui/autocomplete-${info.project.name}.png`,
  });
  expect(
    (
      await new AxeBuilder({ page })
        .include("#header-search-root")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.keyboard.press("ArrowUp");
  await expect(query).toHaveAttribute(
    "aria-activedescendant",
    /query-suggestion-\d+/,
  );
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(query).toHaveValue("a hotel room with an ocean view");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await query.fill("khach san");
  await page.getByRole("option").first().click();
  await expect(query).toHaveValue("a hotel room with an ocean view");
  expect(requests).toBe(0);
  await page
    .getByRole("button", { name: "Gợi ý: Động vật", exact: true })
    .click();
  await expect(query).toHaveValue("a cat sitting by a window");
  expect(requests).toBe(0);
  await expect(
    page.getByRole("button", { name: "Gợi ý: Động vật", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: "Gợi ý: Động vật", exact: true }),
  ).toBeVisible();
  await query.fill("resort");
  await page.keyboard.press("Escape");
  await expect(query).toHaveValue("resort");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await openSettings(page);
  await page.getByRole("button", { name: "Thiên nhiên", exact: true }).click();
  await expect(page.locator("#query")).toHaveValue(
    "a forest landscape with mountains",
  );
  await expect(page.locator("#query")).toBeFocused();
  await accessible(page);
  await revealGallery(page);
  await page.screenshot({
    path: `../docs/verification/consumer_ui/viewport-${info.project.name}.png`,
  });
  await page.screenshot({
    path: `../docs/verification/consumer_ui/home-${info.project.name}.png`,
    fullPage: true,
  });
  const me = (await (await page.request.get("/api/v1/auth/me")).json()).user;
  expect(me.datasets.length).toBeGreaterThan(0);
  const library = me.datasets[0].key as string;
  await openSettings(page);
  await page.getByText("Thư viện và bộ lọc", { exact: true }).click();
  await page.locator("#filter-source").selectOption(library);
  await page.getByText("Thư viện và bộ lọc", { exact: true }).click();
  await page.getByText("Tùy chọn kết quả", { exact: true }).click();
  await page.locator("#top-k").fill("3");
  await page.getByText("Tùy chọn kết quả", { exact: true }).click();
  await page.locator("#query").fill("con meo");
  const text = await search(page);
  expect(text.request().postDataJSON().text).toBe("con meo");
  expect(options(text).filters.source_dataset).toBe(library);
  const results = await text.json();
  expect(results.results[0].metadata.caption).toMatch(/\bcats?\b/i);
  expect(
    results.warnings.some(
      (warning: { code: string }) => warning.code === "QUERY_ACCENTS_RESTORED",
    ),
  ).toBe(true);
  await expect(
    page.getByRole("status").filter({ hasText: "Đã tìm theo “con mèo”" }),
  ).toBeVisible();
  expect(results.effective_settings.text_encoder_manifest_sha256).toMatch(
    /^[a-f0-9]{64}$/,
  );
  expect(
    results.results.every(
      (r: { metadata: { source_dataset: string } }) =>
        r.metadata.source_dataset === library,
    ),
  ).toBe(true);
  await accessible(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/verification/consumer_ui/results-${info.project.name}.png`,
    fullPage: true,
  });
  const open = page.getByRole("button", {
    name: "Phóng to ảnh hạng 1",
    exact: true,
  });
  await open.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate((d) => d.contains(document.activeElement))).toBe(
    true,
  );
  await expect(dialog.getByText("Mã ảnh", { exact: true })).toHaveCount(0);
  await expect(dialog.getByText("Giấy phép", { exact: true })).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(dialog).toContainText("Ảnh 2 / 3");
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(open).toBeFocused();
  await page.getByRole("button", { name: "Tìm bằng ảnh", exact: true }).click();
  await page
    .locator("#reference-image")
    .setInputFiles(
      path.resolve(import.meta.dirname, "../../datasets/sample/coffee.png"),
    );
  await expect(page.getByAltText("Ảnh tham chiếu xem trước")).toBeVisible();
  expect((await (await search(page)).json()).search_mode).toBe("image");
  await page
    .getByRole("button", { name: "Gợi ý: Động vật", exact: true })
    .click();
  await expect(query).toHaveValue("a cat sitting by a window");
  await openSettings(page);
  await expect(page.getByAltText("Ảnh tham chiếu xem trước")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Kết hợp", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.locator("#query").fill("a hotel room");
  expect((await (await search(page)).json()).search_mode).toBe("multimodal");
  await openSettings(page);
  await page.getByRole("button", { name: "Bắt đầu lại", exact: true }).click();
  await expect(page.locator("#query")).toHaveValue("");
  await expect(
    page.getByRole("button", { name: "Mô tả", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByText("Thư viện và bộ lọc", { exact: true }).click();
  await expect(page.locator("#filter-source")).toHaveValue("");
  await page.getByText("Thư viện và bộ lọc", { exact: true }).click();
  await page
    .getByRole("button", { name: "Giao diện tối", exact: true })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".app-header .brand > span").last()).toHaveCSS(
    "color",
    "rgb(237, 245, 239)",
  );
  await accessible(page);
  await revealGallery(page);
  await page.screenshot({
    path: `../docs/verification/consumer_ui/dark-${info.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await page.getByRole("link", { name: "Đăng nhập", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("button", { name: /Vào nhanh Admin/ }).click();
  await expect(
    page.getByRole("heading", { name: "Không gian quản trị", exact: true }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("link", { name: /Quản lý thành viên/ }).click();
  await expect(
    page.getByRole("heading", {
      name: "Tài khoản & quyền truy cập",
      exact: true,
    }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("link", { name: "Tìm ảnh", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Một ý tưởng, nhiều góc nhìn." }),
  ).toBeVisible();
  await accessible(page);
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
});
