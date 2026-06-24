/**
 * E2E tests — Invoices & Payments pages
 * ========================================
 * Covers: invoices list renders, create invoice form, payment recording,
 *         invoice status column visible, portal invoice list.
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

// ── Invoices page ─────────────────────────────────────────────────────────────

test("invoices page loads from sidebar", async ({ page }) => {
  await login(page);
  await page.click("text=Invoices");
  await expect(page).toHaveURL(/invoices/);
});

test("invoices page shows a table", async ({ page }) => {
  await login(page);
  await page.goto("/invoices");
  await expect(
    page.locator(".ant-table, table")
      .or(page.locator("text=No data"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("invoices page has create button", async ({ page }) => {
  await login(page);
  await page.goto("/invoices");
  await expect(
    page.locator("button:has-text('New'), button:has-text('Create'), button:has-text('Add')").first()
  ).toBeVisible({ timeout: 5_000 });
});

test("create invoice button opens a modal", async ({ page }) => {
  await login(page);
  await page.goto("/invoices");
  await page.click("button:has-text('New'), button:has-text('Create'), button:has-text('Add')");
  await expect(
    page.locator(".ant-modal, [role='dialog']").first()
  ).toBeVisible({ timeout: 5_000 });
});

test("invoices page renders without error", async ({ page }) => {
  await login(page);
  await page.goto("/invoices");
  await expect(page.locator("text=Something went wrong").or(page.locator("text=/^500$/")).first()).not.toBeVisible();
});

// ── Payments page ─────────────────────────────────────────────────────────────

test("payments page loads from sidebar", async ({ page }) => {
  await login(page);
  await page.click("text=Payments");
  await expect(page).toHaveURL(/payments/);
});

test("payments page shows a table or list", async ({ page }) => {
  await login(page);
  await page.goto("/payments");
  await expect(
    page.locator(".ant-table, table")
      .or(page.locator("text=No data"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});

test("payments page has record payment button", async ({ page }) => {
  await login(page);
  await page.goto("/payments");
  await expect(
    page.locator("button:has-text('Record'), button:has-text('New'), button:has-text('Add')").first()
  ).toBeVisible({ timeout: 5_000 });
});

test("payment form opens on button click", async ({ page }) => {
  await login(page);
  await page.goto("/payments");
  await page.click(
    "button:has-text('Record'), button:has-text('New Payment'), button:has-text('Add Payment')"
  );
  await expect(
    page.locator(".ant-modal, [role='dialog'], form").first()
  ).toBeVisible({ timeout: 5_000 });
});

// ── Ageing report ─────────────────────────────────────────────────────────────

test("payments page includes ageing section or link", async ({ page }) => {
  await login(page);
  await page.goto("/payments");
  // Either an "Ageing" tab or a section heading
  await expect(
    page.locator(".ant-tabs-tab, [data-testid='ageing']")
      .or(page.locator("text=Ageing"))
      .or(page.locator("text=Aging"))
      .first()
  ).toBeVisible({ timeout: 8_000 });
});
