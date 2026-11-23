import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./consumer-e2e",
  workers: 1,
  retries: 0,
  timeout: 90000,
  globalTimeout: 360000,
  reporter: [["list"], ["json", { outputFile: "test-results/consumer.json" }]],
  use: {
    actionTimeout: 8000,
    navigationTimeout: 10000,
    baseURL: "http://localhost:5173",
    trace: "off",
    screenshot: "off",
    reducedMotion: "reduce",
  },
  projects: [
    {
      name: "desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "narrow",
      use: {
        browserName: "chromium",
        viewport: { width: 320, height: 780 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "firefox",
      use: { browserName: "firefox", viewport: { width: 1280, height: 900 } },
    },
  ],
});
