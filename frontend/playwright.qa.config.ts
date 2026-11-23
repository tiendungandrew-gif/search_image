import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./qa-e2e",
  testMatch: "real.spec.ts",
  timeout: 30000,
  globalTimeout: 240000,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/phase11-real.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5175",
    trace: "off",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "qa-desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "qa-mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "qa-firefox",
      use: { browserName: "firefox", viewport: { width: 1366, height: 900 } },
    },
    {
      name: "qa-webkit",
      use: {
        browserName: "webkit",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
