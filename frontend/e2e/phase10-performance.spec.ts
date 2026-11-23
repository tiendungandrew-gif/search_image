import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("REAL PERF · measured UI timing and lazy network requests", async ({
  page,
}, info) => {
  test.skip(
    process.env.RUN_FRONTEND_PERF !== "1",
    "Chạy riêng để đo, không trộn với functional QA",
  );
  test.setTimeout(90000);
  await page.goto("/");
  await page.locator("#search-token").fill(process.env.API_TOKEN!);
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Dataset sẵn sàng",
  );
  const measurements: Record<string, number>[] = [];
  // Two warmup requests; then 20 measured requests with no LLM calls.
  for (let index = -2; index < 20; index++) {
    await page
      .locator("#query")
      .fill(
        ["a cup of coffee", "a cat", "a beach", "a bicycle"][(index + 2) % 4],
      );
    const pending = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/v1/search") &&
        response.request().method() === "POST",
    );
    const clicked = await page.evaluate(() => performance.now());
    await page
      .getByRole("button", { name: "Tìm kiếm ảnh", exact: true })
      .click();
    const reply = await pending;
    expect(reply.status()).toBe(200);
    const payload = await reply.json();
    await expect(page.locator(".results-section")).toHaveAttribute(
      "data-state",
      "SUCCESS",
    );
    await expect
      .poll(() =>
        page.locator(".results-section").getAttribute("data-first-result-ms"),
      )
      .not.toBeNull();
    await page.locator(".result-card").first().scrollIntoViewIfNeeded();
    await expect
      .poll(() =>
        page.locator(".result-media").first().getAttribute("data-image-ms"),
      )
      .not.toBeNull();
    const row = await page.locator(".results-section").evaluate((node) => {
      const data = (node as HTMLElement).dataset;
      const image = node.querySelector<HTMLElement>(".result-media")!.dataset;
      return {
        api_ms: Number(data.apiMs),
        first_card_ms: Number(data.firstResultMs),
        post_api_frame_ms: Number(data.renderMs),
        react_ms: Number(data.reactMs),
        image_fetch_ms: Number(image.fetchMs),
        image_fetch_decode_ms: Number(image.imageMs),
      };
    });
    const firstImageObserved = await page.evaluate(() => performance.now());
    if (index >= 0)
      measurements.push({
        ...row,
        server_ms: payload.latency.processing_ms,
        browser_observed_image_ms: firstImageObserved - clicked,
      });
  }
  let mediaRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/content?variant=")) mediaRequests++;
  });
  await page.locator("#top-k").fill("50");
  await page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }).click();
  await expect(page.locator(".result-card")).toHaveCount(50);
  await page.waitForTimeout(350);
  expect(mediaRequests).toBeLessThan(50);
  function stats(key: string) {
    const values = measurements.map((row) => row[key]).sort((a, b) => a - b);
    const percentile = (p: number) => {
      const i = (values.length - 1) * p;
      return (
        values[Math.floor(i)] +
        (values[Math.ceil(i)] - values[Math.floor(i)]) * (i % 1)
      );
    };
    return {
      count: values.length,
      p50: percentile(0.5),
      p90: percentile(0.9),
      p95: percentile(0.95),
      min: values[0],
      max: values.at(-1),
    };
  }
  const artifact = {
    verification: "VERIFIED_WITH_REAL_DATA",
    project: info.project.name,
    viewport: page.viewportSize(),
    browser: info.project.use.browserName ?? "chromium",
    runtime:
      "Vite development / local CPU / sequential / no network throttling",
    warmup: 2,
    samples: measurements,
    metrics: Object.fromEntries(
      Object.keys(measurements[0]).map((key) => [key, stats(key)]),
    ),
    top_50_initial_media_requests: mediaRequests,
  };
  const target = path.resolve(
    import.meta.dirname,
    `../../docs/verification/phase10/performance_${info.project.name}.json`,
  );
  fs.writeFileSync(target, JSON.stringify(artifact, null, 2) + "\n");
  await info.attach("frontend-performance", {
    path: target,
    contentType: "application/json",
  });
});
