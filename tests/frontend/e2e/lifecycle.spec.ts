/**
 * E2E tests — Tenant lifecycle enforcement (Phase 1)
 * ===================================================
 * Verifies the frontend never lets a user into the app when the backend blocks
 * login for a suspended / cancelled / expired-trial tenant: the user stays on
 * /login and an error surfaces (rather than reaching /dashboard).
 *
 * Requires: backend + frontend dev servers running, AND a pre-seeded tenant in
 * the relevant lifecycle state. Provide its credentials via env vars; each test
 * skips when its vars are absent so the suite stays CI-safe.
 *
 *   E2E_SUSPENDED_EMAIL / E2E_SUSPENDED_PASSWORD / E2E_SUSPENDED_SLUG
 *   E2E_EXPIRED_TRIAL_EMAIL / E2E_EXPIRED_TRIAL_PASSWORD / E2E_EXPIRED_TRIAL_SLUG
 */
import { test, expect, Page } from "@playwright/test";

async function attemptLogin(page: Page, email: string, password: string, slug?: string) {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", email);
  await page.fill("input[type='password']", password);
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  if (slug && (await tenantInput.count()) > 0) {
    await tenantInput.fill(slug);
  }
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
}

async function expectStaysOnLoginWithError(page: Page) {
  // Must NOT reach the dashboard...
  await expect(page).not.toHaveURL(/dashboard/, { timeout: 8_000 });
  await expect(page).toHaveURL(/login/);
  // ...and an error/notification must be shown to the user.
  await expect(
    page.locator(".ant-message-error, .ant-notification-notice-error, [role='alert']").first()
  ).toBeVisible({ timeout: 8_000 });
}

// ── Suspended tenant ──────────────────────────────────────────────────────────

test("suspended tenant cannot reach the dashboard", async ({ page }) => {
  const email = process.env.E2E_SUSPENDED_EMAIL;
  const password = process.env.E2E_SUSPENDED_PASSWORD;
  const slug = process.env.E2E_SUSPENDED_SLUG;
  test.skip(!email || !password, "Set E2E_SUSPENDED_EMAIL/PASSWORD(/SLUG) to run");

  await attemptLogin(page, email!, password!, slug);
  await expectStaysOnLoginWithError(page);
});

// ── Expired-trial tenant ──────────────────────────────────────────────────────

test("expired-trial tenant cannot reach the dashboard", async ({ page }) => {
  const email = process.env.E2E_EXPIRED_TRIAL_EMAIL;
  const password = process.env.E2E_EXPIRED_TRIAL_PASSWORD;
  const slug = process.env.E2E_EXPIRED_TRIAL_SLUG;
  test.skip(!email || !password, "Set E2E_EXPIRED_TRIAL_EMAIL/PASSWORD(/SLUG) to run");

  await attemptLogin(page, email!, password!, slug);
  await expectStaysOnLoginWithError(page);
});
