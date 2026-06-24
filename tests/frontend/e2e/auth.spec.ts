/**
 * E2E tests — Authentication flows
 * ===================================
 * Covers: login page render, successful login, failed login error,
 *         /auth/me hydration after reload, logout, redirect to /login
 *         when unauthenticated.
 *
 * Requires: backend + frontend dev servers running.
 */
import { test, expect } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@test.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Admin@1234";
const TENANT_SLUG    = process.env.E2E_TENANT_SLUG    ?? "test-tenant";

// ── Login page renders ────────────────────────────────────────────────────────

test("login page has email and password inputs", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("input[type='email'], input#email, input[placeholder*='mail' i]")).toBeVisible();
  await expect(page.locator("input[type='password']")).toBeVisible();
});

test("login page shows submit button", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("button[type='submit'], button:has-text('Sign'), button:has-text('Login')")).toBeVisible();
});

test("login page has CCTV branding text or logo", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveTitle(/CCTV|AMC|Login/i);
});

// ── Redirect unauthenticated ──────────────────────────────────────────────────

test("visiting /dashboard without token redirects to /login", async ({ page }) => {
  await page.goto("/dashboard");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/login/);
});

test("visiting /customers without token redirects to /login", async ({ page }) => {
  await page.goto("/customers");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/customers");
  await expect(page).toHaveURL(/login/);
});

// ── Successful login ──────────────────────────────────────────────────────────

test("successful login redirects to /dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  // Fill tenant slug if the field exists
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  if (await tenantInput.count() > 0) {
    await tenantInput.fill(TENANT_SLUG);
  }
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await expect(page).toHaveURL(/dashboard/, { timeout: 10_000 });
});

test("successful login shows sidebar navigation", async ({ page }) => {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
  // Sidebar should contain navigation items
  await expect(page.locator("text=Dashboard").first()).toBeVisible();
});

// ── Failed login ──────────────────────────────────────────────────────────────

test("wrong password shows error message", async ({ page }) => {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", "wrong-password");
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  // Expect some error/notification to appear
  await expect(
    page.locator(".ant-alert-message, .ant-message-error")
      .or(page.locator("text=Invalid"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("unknown email shows error message", async ({ page }) => {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", "nobody@nowhere.com");
  await page.fill("input[type='password']", "anything");
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await expect(
    page.locator(".ant-alert-message, .ant-message-error")
      .or(page.locator("text=Invalid"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Logout ────────────────────────────────────────────────────────────────────

test("logout clears session and redirects to /login", async ({ page }) => {
  // Login first
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);

  // Click Sign Out
  await page.locator("button:has-text('Sign Out')").or(page.locator("text=Sign Out")).first().click();
  await expect(page).toHaveURL(/login/, { timeout: 8_000 });

  // localStorage must be cleared
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  expect(token).toBeNull();
});

// ── Session persistence ───────────────────────────────────────────────────────

test("logged-in user stays on dashboard after page reload", async ({ page }) => {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
  await page.reload();
  // Should still be on dashboard (not bounced to /login)
  await expect(page).toHaveURL(/dashboard/);
});
