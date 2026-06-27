import { test, expect, type Page } from "@playwright/test";

const ADMIN_EMAIL    = process.env.E2E_ADMIN_EMAIL    ?? "admin@company-e.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "Passw0rd@123";

async function login(page: Page) {
  await page.goto("/login");
  await page.fill("input[type='email'], input#email", ADMIN_EMAIL);
  await page.fill("input[type='password']", ADMIN_PASSWORD);
  await page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')");
  await page.waitForURL(/dashboard/);
}

async function selectFirstOption(page: Page, inputSelector: string) {
  await page.click(inputSelector);
  const dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last();
  await expect(dropdown).toBeVisible({ timeout: 5000 });
  await dropdown.locator(".ant-select-item-option").first().click();
}

async function selectOptionByText(page: Page, inputSelector: string, text: string) {
  await page.click(inputSelector);
  const dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last();
  await expect(dropdown).toBeVisible({ timeout: 5000 });
  await dropdown.locator(`.ant-select-item-option:has-text('${text}')`).first().click();
}

async function waitForModalOpen(page: Page, titleContains: string) {
  const title = page.locator(".ant-modal-title").filter({ visible: true });
  await expect(title).toBeVisible({ timeout: 5000 });
  await expect(title).toContainText(titleContains);
}

async function waitForModalsClosed(page: Page) {
  await expect(page.locator(".ant-modal-wrap").filter({ visible: true })).toHaveCount(0, { timeout: 5000 });
}

async function clickModalButton(page: Page, text: string) {
  await page.locator(".ant-modal-wrap").filter({ visible: true }).locator(`button:has-text('${text}')`).first().click();
}

test.describe("Sales & Rental Module E2E Flows", () => {

  test("Product Catalog crud and page render", async ({ page }) => {
    await login(page);
    
    // Start waiting for the products request
    const responsePromise = page.waitForResponse("**/api/v1/products*");
    await page.goto("/products");
    await responsePromise;
    
    // Check if the page title/header is visible
    await expect(page.locator("text=Product SKU Catalog").first()).toBeVisible();

    // Open add product modal
    await page.click("button:has-text('Add Product')");
    await waitForModalOpen(page, "Product");

    // Fill the product form
    const randomSku = `SKU-E2E-${Date.now()}`;
    await page.fill("input#sku", randomSku);
    await page.fill("input#name", "E2E Dome Camera");
    await page.fill("input#brand", "Hikvision");
    await page.fill("input#model", "DS-Dome");
    
    // Select category (camera)
    await selectOptionByText(page, "input#category", "Camera");

    await page.fill("input#hsn_code", "85258900");
    await page.fill("input#gst_rate", "18");
    await page.fill("input#sale_price", "2500");
    await page.fill("input#rental_price", "250");
    await page.fill("input#warranty_months", "12");

    // Toggle rentable switch (it is the second switch)
    // By default sellable is checked. Let's make sure rentable is checked too
    const switches = page.locator(".ant-modal .ant-switch");
    await switches.nth(1).click(); // rentable is index 1

    // Save/Submit the form
    await clickModalButton(page, "Create");

    // Expect success message
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=Saved"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    // Verify it appeared in the table list
    await expect(page.locator(`text=${randomSku}`).first()).toBeVisible();
  });

  test("Sales Order full lifecycle", async ({ page }) => {
    await login(page);
    
    // Start waiting for products and sales orders requests
    const responsePromise = page.waitForResponse("**/api/v1/products*");
    await page.goto("/sales-orders");
    await responsePromise;
    
    await expect(page.locator("text=Sales Order Management").first()).toBeVisible();

    // Open create sales order modal
    await page.click("button:has-text('New Sales Order')");
    await waitForModalOpen(page, "Sales Order");

    // Select customer
    await selectFirstOption(page, "input#customer_id");

    // Select product SKU
    await selectFirstOption(page, "input#line_items_0_product_id");

    // Quantity & Price
    await page.fill("input#line_items_0_quantity", "1");

    // Click Create
    await clickModalButton(page, "Create");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=created"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    // Confirm the draft order
    await page.click("button:has-text('Confirm')");
    await expect(page.locator("text=CONFIRMED").first()).toBeVisible();

    // Fulfil the order (since product is serial-tracked, we enter serial number)
    await page.click("button:has-text('Fulfil')");
    await waitForModalOpen(page, "Fulfil");
    
    // Fill serial number if input is present
    const serialInput = page.locator("input[placeholder*='serial' i], .ant-modal input[id*='serials']").first();
    if (await serialInput.count() > 0) {
      await serialInput.fill("E2E-SERIAL-999");
    }
    
    await clickModalButton(page, "OK");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=fulfilled"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    await expect(page.locator("text=FULFILLED").first()).toBeVisible();

    // Generate Invoice
    await page.click("button:has-text('Generate Invoice')");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=generated"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });
    await expect(page.locator("text=Billed").first()).toBeVisible();
  });

  test("Rental Registry and Agreements lifecycle", async ({ page }) => {
    await login(page);

    // 1. Create a Rental Unit
    const prodResponsePromise = page.waitForResponse("**/api/v1/products*");
    await page.goto("/rentals/units");
    await prodResponsePromise;
    
    await expect(page.locator("text=Rental Inventory Registry").first()).toBeVisible();

    await page.click("button:has-text('Add Rental Unit')");
    await waitForModalOpen(page, "Rental Unit");

    // Select linked rentable product
    await selectFirstOption(page, "input#product_id");

    // Fill serial
    const randomSerial = `RENT-E2E-${Date.now()}`;
    await page.fill("input#serial_number", randomSerial);
    await page.fill("textarea#notes", "E2E Unit Deploy");

    await clickModalButton(page, "Create");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=Saved"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    await expect(page.locator(`text=${randomSerial}`).first()).toBeVisible();

    // 2. Create Rental Contract
    const contractResponsePromise = page.waitForResponse("**/api/v1/products*");
    await page.goto("/rentals/contracts");
    await contractResponsePromise;
    
    await expect(page.locator("text=Leasing & Rental Contracts").first()).toBeVisible();

    await page.click("button:has-text('New Contract')");
    await waitForModalOpen(page, "Rental Contract");

    // Customer
    await selectFirstOption(page, "input#customer_id");

    // Company
    await selectFirstOption(page, "input#company_id");

    // Select Product line
    await selectFirstOption(page, "input#lines_0_product_id");

    await page.fill("input#lines_0_quantity", "1");
    await page.fill("input#lines_0_unit_price", "500");

    await clickModalButton(page, "Create");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=created"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    // 3. Checkout the physical unit
    await page.click("button:has-text('Check-Out')");
    await waitForModalOpen(page, "Check-Out");

    // Select physical unit serial number
    await selectFirstOption(page, "input#rental_unit_id");

    // Select condition
    await selectFirstOption(page, "input#condition");

    await clickModalButton(page, "OK");
    await expect(
      page.locator("text=checked out")
        .or(page.locator("text=assigned"))
        .first()
    ).toBeVisible({ timeout: 8000 });

    await waitForModalsClosed(page);

    // 4. Activate the rental agreement
    await page.click("button:has-text('Activate')");
    await expect(page.locator("text=ACTIVE").first()).toBeVisible();

    // 5. Run monthly recurring billing
    await page.click("button:has-text('Run Monthly Billing')");
    await waitForModalOpen(page, "Billing");

    // Fill billing run date field
    await page.fill("input#billing_date", "2026-06-27");
    await page.press("input#billing_date", "Enter");

    await clickModalButton(page, "OK");
    await expect(
      page.locator(".ant-message-success")
        .or(page.locator("text=billing"))
        .or(page.locator("text=success"))
        .first()
    ).toBeVisible({ timeout: 8000 });
  });

});
