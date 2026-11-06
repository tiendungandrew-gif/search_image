import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

test("annotation pack hiển thị ảnh thật và không tự xác nhận nhãn", async ({
  page,
}, info) => {
  const file = path.resolve(
    import.meta.dirname,
    "../../.cache/evaluation/annotation.html",
  );
  test.skip(!existsSync(file), "Cần chuẩn bị annotation pack Phase07");
  await page.goto(pathToFileURL(file).href);
  await expect(page.locator(".card")).toHaveCount(10);
  await expect(page.locator("#query option")).toHaveCount(24);
  await expect(page.locator("#progress")).toContainText("0/240 judgments");
  await expect
    .poll(() =>
      page
        .locator(".card img")
        .first()
        .evaluate((image) => (image as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(0);
  await page
    .getByRole("button", { name: "Xuất nhãn đã xác nhận", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Cần tên");
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Xuất bản nháp", exact: true })
    .click();
  const exported = await download;
  const json = JSON.parse(readFileSync((await exported.path())!, "utf8"));
  expect(json.human_verified).toBe(false);
  expect(json.exhaustive_judgments).toBe(false);
  expect(
    Object.values(json.queries).every(
      (value) => Object.keys((value as { grades: object }).grades).length === 0,
    ),
  ).toBe(true);
  await page.screenshot({
    path: info.outputPath("annotation.png"),
    fullPage: true,
  });
});
