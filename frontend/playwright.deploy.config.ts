import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./deploy-e2e",
  testMatch: process.env.DEPLOY_LOGIN_FILE
    ? "accounts.spec.ts"
    : "deployment.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 30000,
  globalTimeout: 180000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/deployment.json" }],
  ],
  use: {
    baseURL: process.env.DEPLOY_BASE_URL ?? "http://127.0.0.1:8088",
    trace: "off",
    screenshot: "off",
  },
  projects: [
    {
      name: "deploy-desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "deploy-mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "deploy-firefox",
      use: { browserName: "firefox", viewport: { width: 1366, height: 900 } },
    },
    {
      name: "deploy-webkit",
      use: {
        browserName: "webkit",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
