import { defineSuite } from "./shared";

export default defineSuite({
  testDir: "../legacy",
  timeout: 30000,
  globalTimeout: 360000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173",
    browserName: "chromium",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "empty-desktop",
      testMatch: "phase10-empty.spec.ts",
      use: {
        baseURL: "http://127.0.0.1:5174",
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "empty-mobile",
      testMatch: "phase10-empty.spec.ts",
      use: {
        baseURL: "http://127.0.0.1:5174",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },

    {
      name: "tablet",
      testMatch: "phase10.spec.ts",
      use: { viewport: { width: 820, height: 1180 }, hasTouch: true },
    },
    {
      name: "firefox",
      testMatch: /(?:foundation|phase10)\.spec\.ts/,
      use: { browserName: "firefox", viewport: { width: 1366, height: 900 } },
    },
    {
      name: "webkit",
      testMatch: /(?:foundation|phase10)\.spec\.ts/,
      use: {
        browserName: "webkit",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },

    {
      name: "desktop",
      testIgnore: "phase10-empty.spec.ts",
      use: { viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "mobile",
      testIgnore: "phase10-empty.spec.ts",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
