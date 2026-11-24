import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";

const indexed = process.env.QA_INDEXED === "1";
test.beforeEach(async ({ page }) => {
  expect(process.env.QA_API_TOKEN, "QA-only token required").toBeTruthy();
  await page.goto("/operator");
  await page.locator("#search-token").fill(process.env.QA_API_TOKEN!);
});

async function submitCore(page: Page) {
  const [response] = await Promise.all([
    page.waitForResponse((reply) =>
      reply.request().method() === "POST" &&
      /\/api\/v1\/search(?:\/multimodal)?$/.test(new URL(reply.url()).pathname),
    ),
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click(),
  ]);
  expect(response.status(), await response.text()).toBe(200);
  await expect(page.locator(".result-card")).toHaveCount(3);
}

test("REAL SERVICES / EMPTY · startup, navigation, data state and accessibility", async ({
  page,
}, info) => {
  test.skip(indexed, "Separate empty-stack profile; no seed imported");
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Chưa có dữ liệu ảnh",
  );
  await expect(
    page.getByText("API đang hoạt động", { exact: true }),
  ).toBeVisible();
  await page.locator("#query").fill("a generated shape");
  await expect(
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".result-card")).toHaveCount(0);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("link", { name: "Đánh giá", exact: true }).click();
  await expect(
    page.getByText(
      /Nguồn benchmark chưa được cấu hình|Chưa có kết quả benchmark/,
    ),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
  await info.attach("classification", {
    body: "VERIFIED_WITH_REAL_SERVICES; empty database, no AI accuracy evidence",
    contentType: "text/plain",
  });
});

test("REAL CLIP / SYNTHETIC · text, image, combined, multi-intent and details", async ({
  page,
}, info) => {
  test.skip(!indexed, "Requires optional cached real-model seed");
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  await page.locator("#top-k").fill("3");
  await page.locator("#query").fill("colored geometric shapes");
  await submitCore(page);
  await expect(page.locator(".result-card img").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Xem chi tiết ảnh hạng 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("qa_synthetic_v1");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("dialog")).toContainText("Ảnh 2 / 3");
  await page.keyboard.press("Escape");
  await page.locator("#mode").selectOption("image");
  await page
    .locator("#reference-image")
    .setInputFiles(
      path.resolve(import.meta.dirname, "../../../../.cache/qa/fixtures/query.png"),
    );
  await expect(page.getByAltText("Ảnh tham chiếu xem trước")).toBeVisible();
  await submitCore(page);
  await page.locator("#mode").selectOption("multimodal");
  await page.locator("#query").fill("colored shapes");
  await submitCore(page);
  await page.locator("#mode").selectOption("multi_intent");
  await page.locator("#query").fill("a rectangle and colored shapes");
  await submitCore(page);
  await expect(page.getByTestId("query-analysis")).toContainText("AND");
  await expect(page.locator(".constraint-evidence").first()).toContainText(
    "Chưa xác minh",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await info.attach("classification", {
    body: "TESTED_WITH_SYNTHETIC_DATA; real CLIP and real private services; semantic relevance NOT_VERIFIED",
    contentType: "text/plain",
  });
});

test("REAL SERVICES / FICTIONAL KB · bounded Agent and disabled RAG", async ({
  page,
}) => {
  test.skip(
    !indexed,
    "Requires optional model seed and isolated fictional knowledge",
  );
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  await page.locator("#mode").selectOption("agent");
  await page
    .locator("#query")
    .fill("Find landmarks in the city where Fixture Lake Alpha is located");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.getByTestId("agent-status")).toContainText("Đã hoàn tất");
  await expect(page.locator(".result-card")).toHaveCount(1);
  await expect(
    page.getByLabel("Các bước đã thực hiện").locator("li"),
  ).toHaveCount(4);
  await expect(
    page.getByRole("button", { name: "Giải thích bằng AI" }),
  ).toHaveCount(0);
  await page
    .locator("#query")
    .fill("Find landmarks in the city where Unknown Fixture Anchor is located");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.locator(".result-card")).toHaveCount(0);
  await expect(page.getByTestId("agent-status")).toContainText(
    "Chưa đủ bằng chứng",
  );
});
