import { expect, test } from "@playwright/test";

test("optional explanation uses real API and preserves indexed image results", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_RAG_E2E !== "1",
    "Requires real RAG provider and API",
  );
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN ?? "");
  await page.locator("#query").fill("a cup of coffee");
  await page.getByRole("button", { name: "Tìm kiếm ảnh" }).click();
  await expect(page.locator(".result-card")).toHaveCount(10);
  await page
    .locator("#rag-question")
    .fill("Metadata ghi định dạng và kích thước như thế nào?");
  await page.getByRole("button", { name: "Giải thích bằng AI" }).click();
  await expect(page.getByTestId("rag-answer")).toContainText("Theo metadata", {
    timeout: 12000,
  });
  await expect(
    page.getByTestId("rag-answer").locator("a").first(),
  ).toHaveAttribute("href", /^#image-[a-f0-9-]+$/);
  await page.getByTestId("rag-answer").locator("a").first().click();
  await expect(page.locator(".result-card")).toHaveCount(10);
  await page.screenshot({
    path: "../docs/verification/phase08/rag.png",
    fullPage: true,
  });
});
