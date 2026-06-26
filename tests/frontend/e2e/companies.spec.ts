import { test, expect, type Page } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@test.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Admin@1234";

async function login(page: Page) {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  if (await tenantInput.count() > 0) {
    await tenantInput.fill("test-tenant");
  }
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
}

test.describe("Multi-Company & Templates Settings", () => {
  test("should navigate to Tenant Settings and show Companies tab", async ({ page }) => {
    await login(page);
    await page.goto("/settings");
    
    // Click on the multi-company tab
    await page.click("text=Multi-Company & Templates");
    
    // Check if the card title is visible
    await expect(page.locator("text=Tenant Operating Entities (Companies)")).toBeVisible();
    await expect(page.locator("button:has-text('Add Company')")).toBeVisible();
  });

  test("should open modal and add a new company", async ({ page }) => {
    await login(page);
    await page.goto("/settings");
    await page.click("text=Multi-Company & Templates");
    
    await page.click("button:has-text('Add Company')");
    
    // Wait for the modal to appear
    const modal = page.locator(".ant-modal");
    await expect(modal).toBeVisible();
    
    // Fill the form fields
    await page.fill("input#name", "Playwright E2E Company");
    await page.fill("input#gstin", "27ABCDE1234F1Z5");
    await page.fill("textarea#address", "101 Playwright Blvd, E2E City");
    
    // Nested inputs (AntD creates name fields like contact_details_email)
    await page.fill("input#contact_details_email", "playwright@company.com");
    await page.fill("input#contact_details_phone", "9876543210");
    
    await page.fill("input#bank_details_bank_name", "E2E Playwright Bank");
    await page.fill("input#bank_details_beneficiary_name", "Playwright E2E Company");
    await page.fill("input#bank_details_account_number", "1234509876");
    await page.fill("input#bank_details_ifsc_code", "PLAY0000123");
    await page.fill("input#bank_details_branch", "Head Office");
    
    await page.fill("input#authorized_signatory_name", "Test Signatory");
    await page.fill("input#authorized_signatory_designation", "Director");
    
    // Submit Form
    await page.click(".ant-modal-footer button:has-text('OK'), button[type='submit']");
    
    // Modal should close and the new company should be listed in the table
    await expect(modal).not.toBeVisible();
    await expect(page.locator("text=Playwright E2E Company")).toBeVisible();
  });

  test("should configure and save JINJA templates for a company", async ({ page }) => {
    await login(page);
    await page.goto("/settings");
    await page.click("text=Multi-Company & Templates");
    
    // Find the row for 'Playwright E2E Company' and click 'Templates'
    const row = page.locator("tr:has-text('Playwright E2E Company')");
    await row.locator("button:has-text('Templates')").click();
    
    // Wait for the templates modal
    const modal = page.locator(".ant-modal");
    await expect(modal).toBeVisible();
    await expect(modal.locator("text=Configure templates for: Playwright E2E Company")).toBeVisible();
    
    // Edit template HTML (Jinja)
    const textarea = page.locator("textarea#template_html");
    await expect(textarea).toBeVisible();
    await textarea.fill("<html><body>Playwright invoice - {{ doc.invoice_number }}</body></html>");
    
    // Save template
    await page.click(".ant-modal-footer button:has-text('OK')");
    
    // The modal should close after successful save
    await expect(modal).not.toBeVisible();
  });
});
