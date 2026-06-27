import { test, expect, type Page } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@company-e.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Passw0rd@123";
const TENANT_SLUG    = process.env.E2E_TENANT_SLUG    ?? "company-e";

async function loginOnTenant(page: Page, tenantUrl: string) {
  await page.goto(tenantUrl + "/login");
  
  // Wait for the public config resolution to finish
  await page.waitForTimeout(1000);
  
  // Verify tenant_slug field is hidden under white-label mode
  const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
  await expect(tenantInput).not.toBeVisible();

  // Fill credentials
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  
  // Click sign in
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/, { timeout: 10000 });
}

test("whitelabel login page branding and hidden slug field", async ({ page }, testInfo) => {
  const baseURL = testInfo.project.use.baseURL || "http://localhost:5173";
  const tenantUrl = baseURL.replace("localhost", `${TENANT_SLUG}.localhost`);

  // Log in using white-labeled subdomain flow
  await loginOnTenant(page, tenantUrl);

  // Check that the sidebar contains the tenant settings link (if admin)
  await expect(page.locator("text=Tenant Settings").first()).toBeVisible();
});

test("tenant admin settings modification including custom email templates", async ({ page }, testInfo) => {
  page.on("console", msg => {
    console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
  });
  page.on("pageerror", err => {
    console.log(`[BROWSER ERROR] ${err.message}`);
  });

  const baseURL = testInfo.project.use.baseURL || "http://localhost:5173";
  const tenantUrl = baseURL.replace("localhost", `${TENANT_SLUG}.localhost`);

  // Log in
  await loginOnTenant(page, tenantUrl);

  // Go to Tenant Settings
  await page.click("text=Tenant Settings");
  await page.waitForURL(/settings/);

  // Switch to the Custom Domain & Mail tab
  await page.click(".ant-tabs-tab-btn:has-text('Custom Domain')");

  // Modify CNAME and SMTP settings
  const customDomainInput = page.locator("input#custom_domain");
  const customSenderInput = page.locator("input#custom_email_sender");
  
  await customDomainInput.clear();
  await customDomainInput.fill(`cname-${TENANT_SLUG}.cctvamc.local`);
  
  await customSenderInput.clear();
  await customSenderInput.fill(`billing@${TENANT_SLUG}.ai`);

  // Expand the Email Templates collapse panel
  const amcPanelHeader = page.locator(".ant-collapse-header:has-text('AMC Expiration')");
  await amcPanelHeader.click();

  // Update AMC template fields
  const subjectInput = page.locator("input#amc_expiry_subject");
  const bodyTextArea = page.locator("textarea#amc_expiry_body");

  await subjectInput.clear();
  await subjectInput.fill("Alert: Your CCTV AMC expires soon");

  await bodyTextArea.clear();
  await bodyTextArea.fill("Dear customer,\n\nWe would like to remind you that your CCTV AMC is expiring.\n\nBest regards.");

  // Save changes
  const saveBtn = page.locator("button:has-text('Save Templates'), button:has-text('Save Domain'), button[type='submit']").last();
  await saveBtn.click();

  // Check message success notification
  const successNotif = page.locator(".ant-message-success").or(page.locator("text=updated successfully")).first();
  await expect(successNotif).toBeVisible({ timeout: 8000 });
});
