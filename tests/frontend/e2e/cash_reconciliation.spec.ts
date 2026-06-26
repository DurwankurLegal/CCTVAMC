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

test.describe("Cash Reconciliation Page", () => {
  let companyId: string;
  let token: string;

  test.beforeAll(async ({ request }) => {
    // 1. Login to get token
    const loginRes = await request.post("http://localhost:8000/api/v1/auth/login", {
      data: {
        email: ADMIN_EMAIL,
        password: ADMIN_PASSWORD,
        tenant_slug: "test-tenant"
      }
    });
    expect(loginRes.ok()).toBeTruthy();
    token = (await loginRes.json()).access_token;

    // 2. Get default/first company
    const compRes = await request.get("http://localhost:8000/api/v1/companies", {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(compRes.ok()).toBeTruthy();
    const companies = await compRes.json();
    expect(companies.length).toBeGreaterThan(0);
    companyId = companies[0].id;

    // 3. Create a pending cash collection record
    const cashRes = await request.post("http://localhost:8000/api/v1/cash-collections", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        customer_name: "Playwright E2E Cust",
        company_id: companyId,
        amount: 4500.00,
        collected_at: new Date().toISOString(),
        remarks: "E2E pending collection test remarks"
      }
    });
    expect(cashRes.ok()).toBeTruthy();
  });

  test("should list pending collections and reconcile one", async ({ page }) => {
    await login(page);
    await page.goto("/reconciliation");

    // Check header title is visible
    await expect(page.locator("text=Employee Cash Reconciliation")).toBeVisible();

    // Verify seeded row is in the table under Pending Verification tab
    const row = page.locator("tr:has-text('Playwright E2E Cust')");
    await expect(row).toBeVisible();
    await expect(row.locator("text=INR 4500.00")).toBeVisible();
    await expect(row.locator("text=PENDING")).toBeVisible();

    // Click Confirm Received button in the row
    await row.locator("button:has-text('Confirm Received')").click();

    // Wait for Review Modal
    const modal = page.locator(".ant-modal");
    await expect(modal).toBeVisible();
    await expect(modal.locator("text=Approve Cash Receipt Handover")).toBeVisible();

    // Fill audit remarks
    await page.fill("textarea#notes", "Physically collected and matched by E2E test");

    // Click OK/Submit in modal
    await page.click(".ant-modal-footer button:has-text('OK'), button[type='submit']");

    // Modal should close and the row should be removed from the Pending Verification tab
    await expect(modal).not.toBeVisible();
    await expect(row).not.toBeVisible();

    // Navigate to History Tab and verify the audited record shows up
    await page.click(".ant-tabs-tab-btn:has-text('Reconciliation History')");
    
    // Check inside history table
    const historyRow = page.locator("tr:has-text('Playwright E2E Cust')");
    await expect(historyRow).toBeVisible();
    await expect(historyRow.locator("text=RECEIVED")).toBeVisible();
    await expect(historyRow.locator("text=\"Physically collected and matched by E2E test\"")).toBeVisible();
  });
});
