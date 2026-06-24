/**
 * E2E tests — Tenant onboarding wizard (Phase 2)
 * ===============================================
 * As a platform admin, onboarding a company shows the first admin's one-time
 * temporary password. Requires a live stack + platform-admin credentials; skips
 * when they're absent (CI-safe, matching the other guarded specs).
 *
 *   E2E_PLATFORM_EMAIL / E2E_PLATFORM_PASSWORD (/ E2E_PLATFORM_SLUG)
 */
import { test, expect } from "@playwright/test";

const EMAIL = process.env.E2E_PLATFORM_EMAIL;
const PASSWORD = process.env.E2E_PLATFORM_PASSWORD;
const SLUG = process.env.E2E_PLATFORM_SLUG;

test("platform admin can onboard a company and see temp credentials", async ({ page }) => {
  test.skip(!EMAIL || !PASSWORD, "Set E2E_PLATFORM_EMAIL/PASSWORD to run");

  // Login as platform admin.
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", EMAIL!);
  await page.fill("input[type='password']", PASSWORD!);
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  if (SLUG && (await tenantInput.count()) > 0) await tenantInput.fill(SLUG);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard|platform/, { timeout: 10_000 });

  // Go to the tenants console and open the onboarding modal.
  await page.goto("/platform/tenants");
  await page.click("button:has-text('Onboard Tenant')");

  // Fill a unique company + first admin.
  const unique = `e2e-${Date.now()}`;
  await page.fill("input[placeholder*='Acme' i]", `E2E ${unique}`);
  await page.fill("input[placeholder*='acme-security' i]", unique);
  await page.fill("input[placeholder*='Jane' i]", "E2E Admin");
  await page.fill("input[placeholder*='admin@' i]", `admin@${unique}.com`);
  await page.click(".ant-modal-footer button:has-text('Create')");

  // The one-time credentials modal appears with a temporary password.
  await expect(page.locator("text=Company onboarded")).toBeVisible({ timeout: 10_000 });
  await expect(page.locator("text=temporary password")).toBeVisible();
});
