import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("REAL EMPTY · isolated PostgreSQL/Qdrant/MinIO and disabled AI features", async ({
  page,
}, info) => {
  test.skip(!process.env.API_TOKEN, "Cần môi trường rỗng tạm và read token");
  const posts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST")
      posts.push(new URL(request.url()).pathname);
  });
  await page.goto("/");
  await expect(
    page.getByText("API đang hoạt động", { exact: true }),
  ).toBeVisible();
  const snapshot = page.waitForResponse((response) =>
    response.url().endsWith("/system/workspace"),
  );
  await page.locator("#search-token").fill(process.env.API_TOKEN!);
  const response = await snapshot;
  expect(response.status()).toBe(200);
  const payload = await response.json();
  expect(payload.dataset.state).toBe("empty_dataset");
  expect(payload.dataset.images).toBe(0);
  expect(payload.dataset.indexed_images).toBe(0);
  expect(
    Object.values(payload.capabilities).every((value) => value === false),
  ).toBe(true);
  expect(payload.dependencies).toMatchObject({
    postgresql: "healthy",
    qdrant: "healthy",
    minio: "healthy",
  });
  await expect(page.getByTestId("dataset-status")).toContainText(
    "Chưa có dữ liệu ảnh",
  );
  await page.locator("#query").fill("a coffee shop");
  await expect(
    page.getByRole("button", { name: "Tìm kiếm ảnh", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".result-card")).toHaveCount(0);
  await expect(page.locator('option[value="agent"]')).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Giải thích bằng AI" }),
  ).toHaveCount(0);
  expect(posts).toEqual([]);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await info.attach("real-empty-workspace", {
    body: JSON.stringify(payload),
    contentType: "application/json",
  });
  await page.screenshot({
    path: info.outputPath("real-empty.png"),
    fullPage: true,
  });
});

test("REAL EMPTY · evaluation remains navigable without benchmark artifacts", async ({
  page,
}) => {
  await page.goto("/evaluation");
  await page.locator("#evaluation-token").fill(process.env.API_TOKEN!);
  await expect(
    page.getByText("Chưa có kết quả benchmark.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
  await page.getByRole("link", { name: "Khám phá", exact: true }).click();
  await expect(page.locator("#query")).toBeVisible();
});
