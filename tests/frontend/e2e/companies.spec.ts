import { test, expect, type Page } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@company-e.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Passw0rd@123";
const TENANT_SLUG    = process.env.E2E_TENANT_SLUG    ?? "company-e";

async function login(page: Page) {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  if (await tenantInput.count() > 0) {
    await tenantInput.fill(TENANT_SLUG);
  }
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
}

test.describe("Multi-Company & Templates Settings", () => {
  const companyName = `Playwright E2E Company ${Math.floor(Math.random() * 1000000)}`;

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
    
    // Fill the form fields inside the modal to avoid collisions with the parent settings page
    await modal.locator("input#name").fill(companyName);
    await modal.locator("input#gstin").fill("27ABCDE1234F1Z5");
    await modal.locator("textarea#address").fill("101 Playwright Blvd, E2E City");
    
    // Nested inputs (AntD creates name fields like contact_details_email)
    await modal.locator("input#contact_details_email").fill("playwright@company.com");
    await modal.locator("input#contact_details_phone").fill("9876543210");
    
    await modal.locator("input#bank_details_bank_name").fill("E2E Playwright Bank");
    await modal.locator("input#bank_details_beneficiary_name").fill(companyName);
    await modal.locator("input#bank_details_account_number").fill("1234509876");
    await modal.locator("input#bank_details_ifsc_code").fill("PLAY0000123");
    await modal.locator("input#bank_details_branch").fill("Head Office");
    
    await modal.locator("input#authorized_signatory_name").fill("Test Signatory");
    await modal.locator("input#authorized_signatory_designation").fill("Director");
    
    // Submit Form
    await modal.locator("button:has-text('OK'), button[type='submit']").click();
    
    // Modal should close and the new company should be listed in the table
    await expect(modal).not.toBeVisible();
    await expect(page.locator(`text=${companyName}`)).toBeVisible();
  });

  test("should configure and save JINJA templates for a company", async ({ page }) => {
    await login(page);
    await page.goto("/settings");
    await page.click("text=Multi-Company & Templates");
    
    // Find the row for companyName and click 'Templates'
    const row = page.locator(`tr:has-text('${companyName}')`);
    await row.locator("button:has-text('Templates')").click();
    
    // Wait for the templates modal
    const modal = page.locator(".ant-modal");
    await expect(modal).toBeVisible();
    await expect(modal.locator(`text=Configure templates for: ${companyName}`)).toBeVisible();
    
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
