/**
 * E2E tests — Customer Self-Service Portal
 * ==========================================
 * Covers: portal login page renders, failed login, successful portal login,
 *         portal dashboard visible, portal tickets list, portal invoices list,
 *         portal coverage page.
 *
 * Note: Portal uses a separate auth flow (/portal/login).
 */
import { test, expect, type Page } from "@playwright/test";

const PORTAL_EMAIL    = process.env.E2E_PORTAL_EMAIL    ?? "customer@portal.com";
const PORTAL_PASSWORD = process.env.E2E_PORTAL_PASSWORD ?? "Portal@1234";
const TENANT_SLUG    = process.env.E2E_TENANT_SLUG    ?? "durwankur";

async function portalLogin(page: Page) {
  await page.goto("/portal/login");
  await page.fill("#tenant_slug", TENANT_SLUG);
  await page.fill("input[type='email'], input#email", PORTAL_EMAIL);
  await page.fill("input[type='password']", PORTAL_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/\/portal\/?$/, { timeout: 10_000 });
}

// ── Portal login page ─────────────────────────────────────────────────────────

test("portal login page is accessible", async ({ page }) => {
  await page.goto("/portal/login");
  await expect(page).toHaveURL(/portal\/login/);
});

test("portal login page has email and password inputs", async ({ page }) => {
  await page.goto("/portal/login");
  await expect(page.locator("input[type='email'], input#email").first()).toBeVisible();
  await expect(page.locator("input[type='password']").first()).toBeVisible();
});

test("portal login page is separate from staff login", async ({ page }) => {
  await page.goto("/portal/login");
  // Should not redirect to staff dashboard
  await expect(page).toHaveURL(/portal\/login/);
});

test("invalid portal credentials shows error", async ({ page }) => {
  await page.goto("/portal/login");
  await page.fill("#tenant_slug", TENANT_SLUG);
  await page.fill("input[type='email'], input#email", "fake@portal.com");
  await page.fill("input[type='password']", "wrongpass");
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await expect(
    page.locator(".ant-message-error, [role='alert']")
      .or(page.locator("text=Invalid"))
      .or(page.locator("text=credentials"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Portal dashboard ──────────────────────────────────────────────────────────

test("portal dashboard loads after login", async ({ page }) => {
  await portalLogin(page);
  await expect(page).toHaveURL(/portal/);
  await expect(
    page.locator("h1, h2, .ant-card, [data-testid='portal-dashboard']").first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Portal navigation ─────────────────────────────────────────────────────────

test("portal has tickets link", async ({ page }) => {
  await portalLogin(page);
  await expect(
    page.locator("a[href*='/portal/tickets']")
      .or(page.locator("text=Tickets"))
      .or(page.locator("text=Service Requests"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("portal has invoices link", async ({ page }) => {
  await portalLogin(page);
  await expect(
    page.locator("a[href*='/portal/invoices']")
      .or(page.locator("text=Invoices"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("portal has coverage/AMC link", async ({ page }) => {
  await portalLogin(page);
  await expect(
    page.locator("a[href*='/portal/coverage']")
      .or(page.locator("text=Coverage"))
      .or(page.locator("text=AMC"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Portal sub-pages ──────────────────────────────────────────────────────────

test("portal tickets page loads", async ({ page }) => {
  await portalLogin(page);
  await page.goto("/portal/tickets");
  await expect(
    page.locator(".ant-table, table")
      .or(page.locator("text=No data"))
      .or(page.locator("text=No tickets"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("portal invoices page loads", async ({ page }) => {
  await portalLogin(page);
  await page.goto("/portal/invoices");
  await expect(
    page.locator(".ant-table, table")
      .or(page.locator("text=No data"))
      .or(page.locator("text=No invoices"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("portal coverage page loads", async ({ page }) => {
  await portalLogin(page);
  await page.goto("/portal/coverage");
  await expect(
    page.locator(".ant-card, .ant-list")
      .or(page.locator("text=No data"))
      .or(page.locator("text=coverage"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Portal isolation from staff app ──────────────────────────────────────────

test("portal login token does not grant access to staff dashboard", async ({ page }) => {
  await portalLogin(page);
  // Manually navigate to staff route
  await page.goto("/dashboard");
  // Wait for the asynchronous client-side redirect to the login page to complete
  await page.waitForURL(/\/login/);
  // Should redirect away or show 403, not the staff dashboard
  // The staff app checks for a different token type; portal token is invalid
  const url = page.url();
  expect(url).not.toMatch(/^http:\/\/localhost:\d+\/dashboard$/);
});
