// Validate the actual offline review page without creating human judgments.
import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(path.resolve("frontend/package.json"));
const { chromium, expect } = require("@playwright/test");
const input =
  process.argv[2] ?? ".cache/evaluation/rag_phase08_coco_review.html";
const output = process.argv[3];
const browser = await chromium.launch();
const errors = [],
  remote = [];
try {
  const page = await browser.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) remote.push(request.url());
  });
  await page.goto(pathToFileURL(path.resolve(input)).href);
  await expect(
    page.getByRole("heading", {
      name: "Đánh giá câu trả lời RAG trên dữ liệu thực",
    }),
  ).toBeVisible();
  const cases = await page.locator("#case option").count();
  expect(cases).toBeGreaterThan(0);
  await expect(page.locator("#images img").first()).toBeVisible();
  expect(
    await page
      .locator("#images img")
      .evaluateAll((images) =>
        images.every((i) => i.complete && i.naturalWidth > 0),
      ),
  ).toBe(true);
  await page.getByRole("button", { name: "Xuất nhãn đã xác nhận" }).click();
  await expect(page.getByRole("alert")).toContainText("Cần tên");
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất bản nháp" }).click();
  const download = await pending;
  const draft = JSON.parse(await readFile(await download.path(), "utf8"));
  expect(draft.human_verified).toBe(false);
  expect(Object.keys(draft.cases)).toHaveLength(cases);
  expect(
    Object.values(draft.cases).every((row) =>
      Object.values(row).every((value) => value === null),
    ),
  ).toBe(true);
  expect(errors).toHaveLength(0);
  expect(remote).toHaveLength(0);
  await download.delete();
  const report = {
    status: "pass",
    cases,
    human_verified: false,
    images_loaded: true,
    verified_export_without_review: "rejected",
    javascript_errors: errors.length,
    remote_requests: remote.length,
    draft_grades: "all null",
  };
  if (output) await writeFile(output, JSON.stringify(report, null, 2) + "\n");
  process.stdout.write(JSON.stringify(report) + "\n");
} finally {
  await browser.close();
}
