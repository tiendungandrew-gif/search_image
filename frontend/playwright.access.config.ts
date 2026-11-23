import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./access-e2e",
  workers: 1,
  retries: 0,
  timeout: 90000,
  globalTimeout: 300000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/access-control.json" }],
  ],
  use: {
    baseURL: process.env.ACCESS_BASE_URL ?? "http://127.0.0.1:5175",
    trace: "off",
    screenshot: "off",
  },
  projects: [
    {
      name: "access-desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "access-mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
