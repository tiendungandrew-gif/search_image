import { defineSuite } from "./shared";
export default defineSuite({
  testDir: "../quick-login",
  timeout: 60000,
  globalTimeout: 180000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/quick-login.json" }],
  ],
  use: {
    baseURL: process.env.QUICK_LOGIN_BASE_URL ?? "http://localhost:5173",
    screenshot: "off",
  },
  projects: [
    {
      name: "quick-desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "quick-mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
