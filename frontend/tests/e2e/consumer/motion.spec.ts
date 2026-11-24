import { expect, test } from "@playwright/test";

test.use({ video: { mode: "on", size: { width: 960, height: 680 } } });

test("motion: gallery, density, image navigation and reduced motion", async ({
  page,
}, info) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  let searches = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      /\/api\/v1\/search(?:\/multimodal)?$/.test(
        new URL(request.url()).pathname,
      )
    )
      searches++;
  });
  await page.goto("/login");
  const quick = page.getByRole("button", { name: /Vào nhanh User/ });
  const retry = page.getByRole("button", {
    name: "Kiểm tra lại kết nối",
    exact: true,
  });
  await expect(quick.or(retry).first()).toBeVisible({ timeout: 15000 });
  if (await retry.isVisible()) await retry.click();
  await quick.click();
  const cards = page.locator(".result-card:not(.skeleton)");
  await expect(cards).toHaveCount(12);
  await cards.first().scrollIntoViewIfNeeded();
  await expect(cards.first().locator(".result-media")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(cards.first().locator("img")).toHaveCSS("opacity", "1");
  expect(
    await cards
      .first()
      .evaluate((node) => getComputedStyle(node).animationName),
  ).toBe("lens-card-in");
  const order = await cards.evaluateAll((nodes) =>
    nodes.map((node) => node.id),
  );
  const beforeSearches = searches;
  await page.getByRole("button", { name: "Lưới gọn", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Lưới gọn", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    await cards.evaluateAll((nodes) => nodes.map((node) => node.id)),
  ).toEqual(order);
  expect(searches).toBe(beforeSearches);
  if (
    await page.evaluate(
      () => matchMedia("(hover: hover) and (pointer: fine)").matches,
    )
  ) {
    const topic = page.locator(".travel-topic").first();
    await topic.hover();
    await expect(topic).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -3)");
    await page.mouse.down();
    await expect(topic).toHaveCSS(
      "transform",
      "matrix(0.97, 0, 0, 0.97, 0, 0)",
    );
    await page.mouse.move(0, 0);
    await page.mouse.up();
  }
  const opener = cards
    .first()
    .getByRole("button", { name: /Phóng to ảnh hạng/ });
  await opener.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  expect(
    await dialog.evaluate((node) => getComputedStyle(node).animationName),
  ).toBe("lens-dialog-in");
  await expect(dialog.locator(".result-media")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await expect(dialog.locator("img")).toHaveCSS("opacity", "1");
  await expect
    .poll(() =>
      dialog.evaluate((node) => {
        const rect = node.getBoundingClientRect();
        return Math.max(
          Math.abs(rect.x + rect.width / 2 - innerWidth / 2),
          Math.abs(rect.y + rect.height / 2 - innerHeight / 2),
        );
      }),
    )
    .toBeLessThan(2);
  await dialog.screenshot({
    path: `../docs/verification/consumer_motion/dialog-${info.project.name}.png`,
  });
  await page.keyboard.press("ArrowRight");
  await expect(dialog.locator("#detail-position")).toContainText("Ảnh 2 / 12");
  await expect(dialog.locator(".result-media")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(opener).toBeFocused();
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await cards
      .first()
      .evaluate((node) => getComputedStyle(node).animationName),
  ).toBe("none");
  expect(
    await cards
      .first()
      .locator("img")
      .evaluate((node) => getComputedStyle(node).transitionDuration),
  ).toBe("0s");
  await opener.click();
  await expect(dialog).toBeVisible();
  expect(
    await dialog.evaluate((node) => getComputedStyle(node).animationName),
  ).toBe("none");
  await page
    .getByRole("button", { name: "Đóng chi tiết ảnh", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(opener).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
