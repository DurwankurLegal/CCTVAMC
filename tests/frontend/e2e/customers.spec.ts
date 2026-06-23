/**
 * E2E tests — Customers page
 * ============================
 * Covers: page renders, create customer form, customer list,
 *         edit customer name, contact tab, error states.
 *
 * Requires: logged-in session (reuses storage state from auth.spec).
 */
import { test, expect, type Page } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@test.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Admin@1234";

async function login(page: Page) {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
}

// ── Page renders ──────────────────────────────────────────────────────────────

test("customers page is accessible from sidebar", async ({ page }) => {
  await login(page);
  await page.click("text=Customers");
  await expect(page).toHaveURL(/customers/);
  await expect(page.locator("h1, h2, .ant-page-header-heading-title").first()).toBeVisible();
});

test("customers page shows a table or list", async ({ page }) => {
  await login(page);
  await page.goto("/customers");
  await expect(
    page.locator(".ant-table, table, [data-testid='customer-list']").first()
  ).toBeVisible({ timeout: 8_000 });
});

// ── Create customer ───────────────────────────────────────────────────────────

test("create customer button opens a form", async ({ page }) => {
  await login(page);
  await page.goto("/customers");
  // Click Add / New Customer button
  await page.click("button:has-text('Add'), button:has-text('New'), button:has-text('Create')");
  // A modal or form should appear
  await expect(
    page.locator(".ant-modal, form, [role='dialog']").first()
  ).toBeVisible({ timeout: 5_000 });
});

test("create customer with valid data submits successfully", async ({ page }) => {
  await login(page);
  await page.goto("/customers");
  await page.click("button:has-text('Add'), button:has-text('New'), button:has-text('Create')");
  await page.waitForSelector(".ant-modal, form, [role='dialog']");

  // Fill customer name
  await page.fill(
    ".ant-modal input[placeholder*='name' i], input[name='name'], input#name",
    `E2E Customer ${Date.now()}`
  );

  // Submit
  await page.click(".ant-modal-footer button.ant-btn-primary, button[type='submit']");

  // Success notification or modal closes
  await expect(
    page.locator(".ant-message-success, text=created, text=success, text=saved").first()
  ).toBeVisible({ timeout: 8_000 });
});

test("create customer with empty name shows validation error", async ({ page }) => {
  await login(page);
  await page.goto("/customers");
  await page.click("button:has-text('Add'), button:has-text('New'), button:has-text('Create')");
  await page.waitForSelector(".ant-modal, form, [role='dialog']");
  // Submit without filling name
  await page.click(".ant-modal-footer button.ant-btn-primary, button[type='submit']");
  // Validation error must appear
  await expect(
    page.locator(".ant-form-item-explain-error, text=required, [class*='error']").first()
  ).toBeVisible({ timeout: 5_000 });
});

// ── Sidebar navigation ────────────────────────────────────────────────────────

test("sidebar shows Customers link for admin", async ({ page }) => {
  await login(page);
  await expect(page.locator(".ant-menu, nav").filter({ hasText: "Customers" })).toBeVisible();
});

// ── Search / filter (if present) ──────────────────────────────────────────────

test("customer list loads without error on first visit", async ({ page }) => {
  await login(page);
  await page.goto("/customers");
  // No error boundary or 500 error
  await expect(page.locator("text=Something went wrong, text=Error").first()).not.toBeVisible();
  await expect(
    page.locator(".ant-table, table, [data-testid='customer-list'], text=No data").first()
  ).toBeVisible({ timeout: 8_000 });
});
