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

test.describe("Cash Reconciliation Page", () => {
  const customerName = `Playwright E2E Cust ${Math.floor(Math.random() * 1000000)}`;
  let companyId: string;
  let token: string;

  test.beforeAll(async ({ request }) => {
    // 1. Login to get token
    const loginRes = await request.post("http://localhost:8000/api/v1/auth/login", {
      data: {
        email: ADMIN_EMAIL,
        password: ADMIN_PASSWORD,
        tenant_slug: TENANT_SLUG
      }
    });
    expect(loginRes.ok()).toBeTruthy();
    token = (await loginRes.json()).access_token;

    // 2. Create a Company to ensure one exists
    const createCompRes = await request.post("http://localhost:8000/api/v1/companies", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: "Test E2E Reconcile Company",
        gst_status: "NON_GST",
        address: "E2E office",
        contact_details: {},
        bank_details: {},
        authorized_signatory: {},
        is_default: true
      }
    });
    expect(createCompRes.ok()).toBeTruthy();
    companyId = (await createCompRes.json()).id;

    // 3. Create a pending cash collection record
    const cashRes = await request.post("http://localhost:8000/api/v1/cash-collections", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        customer_name: customerName,
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
    const row = page.locator(`.ant-tabs-tabpane-active tr:has-text('${customerName}')`);
    await expect(row).toBeVisible();
    await expect(row.locator("text=INR 4500.00")).toBeVisible();
    await expect(row.locator("span.ant-tag:has-text('PENDING')")).toBeVisible();

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
    const historyRow = page.locator(`.ant-tabs-tabpane-active tr:has-text('${customerName}')`);
    await expect(historyRow).toBeVisible();
    await expect(historyRow.locator("span.ant-tag:has-text('RECEIVED')")).toBeVisible();
    await expect(historyRow.locator("text=Physically collected and matched by E2E test")).toBeVisible();
  });

  test("should allow admin to manually add and edit a cash collection record", async ({ page }) => {
    const manualCustomerName = `Manual E2E Cust ${Math.floor(Math.random() * 1000000)}`;
    await login(page);
    await page.goto("/reconciliation");

    // 1. Click Add Record
    await page.click("button:has-text('Add Record')");

    // Wait for Add modal
    const modal = page.locator(".ant-modal");
    await expect(modal).toBeVisible();
    await expect(modal.locator("text=Add Cash Collection Record")).toBeVisible();

    // Fill form
    // Select Employee
    await modal.locator(".ant-form-item:has-text('Employee')").click();
    await page.locator(".ant-select-dropdown:visible .ant-select-item-option-content:has-text('Admin')").first().click();

    // Select Company
    await modal.locator(".ant-form-item:has-text('Operating Company')").click();
    await page.locator(".ant-select-dropdown:visible .ant-select-item-option-content:has-text('Test E2E Reconcile Company')").first().click();

    // Fill Customer Name
    await modal.locator("input#customer_name").fill(manualCustomerName);

    // Fill Amount
    await modal.locator("input#amount").fill("2500.00");

    // Fill Collected Date & Time
    await modal.locator("input#collected_at").click();
    await page.click("a.ant-picker-now-btn"); // Click 'Now' in datepicker

    // Remarks
    await modal.locator("textarea#remarks").fill("Manually logged by E2E test");

    // Click OK
    await page.click(".ant-modal-footer button:has-text('OK'), button[type='submit']");

    // Modal should close and the new row should be listed in the table
    await expect(modal).not.toBeVisible();
    const row = page.locator(`.ant-tabs-tabpane-active tr:has-text('${manualCustomerName}')`);
    await expect(row).toBeVisible();
    await expect(row.locator("text=INR 2500.00")).toBeVisible();

    // 2. Edit the record
    await row.locator("button:has-text('Edit')").click();
    await expect(modal).toBeVisible();
    await expect(modal.locator("text=Edit Cash Collection Record")).toBeVisible();

    // Modify Customer Name and Amount
    const updatedCustomerName = `${manualCustomerName} Edited`;
    await modal.locator("input#customer_name").fill(updatedCustomerName);
    await modal.locator("input#amount").fill("3000.00");

    // Save Edit
    await page.click(".ant-modal-footer button:has-text('OK'), button[type='submit']");

    // Verify modal closes and updated values are listed
    await expect(modal).not.toBeVisible();
    const updatedRow = page.locator(`.ant-tabs-tabpane-active tr:has-text('${updatedCustomerName}')`);
    await expect(updatedRow).toBeVisible();
    await expect(updatedRow.locator("text=INR 3000.00")).toBeVisible();
  });
});
