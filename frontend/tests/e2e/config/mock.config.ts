import { defineSuite } from "./shared";

export default defineSuite({
  testDir: "../qa",
  testMatch: "mock.spec.ts",
  timeout: 20000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/phase11-mock.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5190",
    browserName: "chromium",
  },
  webServer: {
    command: "npm --prefix frontend run dev -- --host 127.0.0.1 --port 5190",
    cwd: "../../../..",
    url: "http://127.0.0.1:5190",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
