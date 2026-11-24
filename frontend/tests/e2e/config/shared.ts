import { defineConfig, type PlaywrightTestConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

// Absolute paths keep suite discovery stable through the default config wrapper.
export function defineSuite(config: PlaywrightTestConfig) {
  return defineConfig({
    ...config,
    testDir: fileURLToPath(new URL(config.testDir!, import.meta.url)),
    workers: 1,
    retries: 0,
    // Traces can contain session/diagnostic headers.
    use: { ...config.use, trace: "off" },
  });
}
