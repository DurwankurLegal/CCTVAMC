import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for CCTV AMC E2E tests.
 * 
 * Prerequisites:
 *   1. Backend running at http://localhost:8000
 *   2. Frontend running at http://localhost:5173
 *
 * Run:
 *   npx playwright install chromium
 *   npx playwright test
 */
export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.ts",
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: 1,           // serial to avoid shared-DB race conditions in dev
  reporter: [["html", { outputFolder: "playwright-report" }], ["list"]],

  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    headless: true,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
