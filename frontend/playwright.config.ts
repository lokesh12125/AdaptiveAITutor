import { defineConfig, devices } from "@playwright/test";

/** Runs against an already running stack: see README ("Run the tests"). */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5173", trace: "retain-on-failure", screenshot: "only-on-failure", actionTimeout: 15_000 },
  // E2E_CHROME_CHANNEL=chrome uses an installed Chrome (in a temporary profile) instead of Playwright's download.
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, channel: process.env.E2E_CHROME_CHANNEL || undefined } }],
});
