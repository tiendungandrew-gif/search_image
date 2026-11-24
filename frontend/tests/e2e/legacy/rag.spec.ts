import { expect, test } from "@playwright/test";

test("optional explanation uses real API and preserves indexed image results", async ({
  page,
}, info) => {
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
  const pending = page.waitForResponse((r) =>
    /\/rag\/explain(?:\/stream)?$/.test(r.url()),
  );
  await page.getByRole("button", { name: "Giải thích bằng AI" }).click();
  const response = await pending;
  expect(response.status()).toBe(200);
  const content = await response.text();
  const headers = response.headers();
  const streaming = headers["content-type"].includes("text/event-stream");
  const payload = streaming
    ? JSON.parse(
        content
          .split(/\r?\n\r?\n/)
          .find((frame) => frame.startsWith("event: generation_completed"))!
          .split(/\r?\n/)
          .find((line) => line.startsWith("data:"))!
          .slice(5),
      )
    : JSON.parse(content);
  await info.attach("real-rag-outcome", {
    body: JSON.stringify({
      generated: payload.rag.generated,
      grounding_status: payload.rag.grounding_status,
      error_code: payload.rag.error_code,
      citation_count: payload.rag.citations.length,
    }),
    contentType: "application/json",
  });
  await expect(page.getByTestId("rag-answer")).toContainText(
    payload.rag.answer,
  );
  if (payload.rag.generated && payload.rag.citations.length > 0) {
    expect(payload.rag.citations.length).toBeGreaterThan(0);
    const citation = page.getByTestId("rag-answer").locator("a").first();
    await expect(citation).toHaveAttribute("href", /^#image-[a-f0-9-]+$/);
    await citation.click();
  } else {
    expect(["insufficient_evidence", "generation_unavailable"]).toContain(
      payload.rag.grounding_status,
    );
    await expect(page.getByTestId("rag-answer").locator("a")).toHaveCount(0);
  }
  await expect(page.locator(".result-card")).toHaveCount(10);
  await page.screenshot({
    path: info.outputPath("rag.png"),
    fullPage: true,
  });
});
