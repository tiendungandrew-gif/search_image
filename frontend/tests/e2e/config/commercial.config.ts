import { defineSuite } from "./shared";
export default defineSuite({
  testDir: "../commercial",
  timeout: 90000,
  globalTimeout: 360000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/commercial.json" }],
  ],
  use: {
    baseURL: "http://localhost:5173",
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
