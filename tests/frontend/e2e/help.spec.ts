import { test, expect } from "@playwright/test";

test.describe("Help Center E2E Tests", () => {

  test.beforeEach(async ({ page }) => {
    // Set viewport size to ensure desktop layout
    await page.setViewportSize({ width: 1600, height: 1200 });
    
    // Log console messages and errors for easier debugging
    page.on("console", msg => console.log("BROWSER CONSOLE:", msg.text()));
    page.on("pageerror", err => console.error("BROWSER PAGE ERROR:", err.message));
  });

  test("Company A (Sales only) menu filtering and article feedback", async ({ page }) => {
    // 1. Login as Company A Admin
    await page.goto("/login");
    await page.fill("input[type='email'], input#email", "admin@company-a.com");
    await page.fill("input[type='password']", "Passw0rd@123");
    
    // Fill tenant slug
    const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
    if (await tenantInput.count() > 0) {
      await tenantInput.fill("company-a");
    }
    
    await page.click("button[type='submit']");
    await page.waitForURL(/dashboard/, { timeout: 15000 });

    // 2. Navigate to Help Center
    await page.goto("/help");
    await page.waitForURL(/help\/introduction/, { timeout: 15000 });

    // 3. Verify category visibility in Sidebar (scoped to Help Center Documentation sider)
    const sidebar = page.locator(".ant-layout-sider").filter({ hasText: "Documentation" }).locator(".ant-menu").first();
    await expect(sidebar).toBeVisible({ timeout: 15000 });
    await expect(sidebar).toContainText("Getting Started");
    await expect(sidebar).toContainText("CRM (Core)");
    await expect(sidebar).toContainText("Sales");

    // AMC and Rental must be hidden for Company A
    await expect(sidebar).not.toContainText("Rental");
    await expect(sidebar).not.toContainText("AMC & Service");

    // 4. Click an article link in sidebar (expand Getting Started category first)
    await sidebar.locator("text=Getting Started").click();
    await sidebar.locator("text=Login & 2FA Setup").click();
    await page.waitForURL(/help\/login-and-2fa/, { timeout: 15000 });
    
    // Verify title and purpose
    await expect(page.locator("h1")).toHaveText("Login & 2FA Setup", { timeout: 15000 });
    await expect(page.locator("text=Purpose: Instructions on logging in")).toBeVisible({ timeout: 15000 });

    // 5. Submit feedback rating
    await expect(page.locator("text=Was this article helpful?")).toBeVisible({ timeout: 15000 });
    await page.click("button:has-text('Yes, helpful')");
    await expect(page.locator("text=Rate article quality:")).toBeVisible({ timeout: 15000 });
    
    // Fill comment and submit (Yes, helpful button already set rating to 5 stars)
    await page.fill("textarea", "Amazing, crystal clear instructions!");
    await page.click("button:has-text('Submit Feedback')");
    
    // Verify feedback thank-you card appears
    await expect(page.locator("text=Thank you! Your feedback helps us")).toBeVisible({ timeout: 15000 });
  });

  test("Company C (AMC only) hides Sales & Rental", async ({ page }) => {
    // 1. Login as Company C Admin
    await page.goto("/login");
    await page.fill("input[type='email'], input#email", "admin@company-c.com");
    await page.fill("input[type='password']", "Passw0rd@123");
    
    // Fill tenant slug
    const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
    if (await tenantInput.count() > 0) {
      await tenantInput.fill("company-c");
    }
    
    await page.click("button[type='submit']");
    await page.waitForURL(/dashboard/, { timeout: 15000 });

    // 2. Navigate to Help Center
    await page.goto("/help");
    await page.waitForURL(/help\/introduction/, { timeout: 15000 });

    // 3. Verify category visibility in Sidebar (scoped to Help Center Documentation sider)
    const sidebar = page.locator(".ant-layout-sider").filter({ hasText: "Documentation" }).locator(".ant-menu").first();
    await expect(sidebar).toBeVisible({ timeout: 15000 });
    await expect(sidebar).toContainText("Getting Started");
    await expect(sidebar).toContainText("CRM (Core)");
    await expect(sidebar).toContainText("AMC & Service");

    // Rental must be hidden entirely.
    // Optional Sales articles must be hidden, though Sales category code text remains 
    // due to Generating Invoices (core article).
    await expect(sidebar).not.toContainText("Rental");
    await expect(sidebar).not.toContainText("Creating Quotations");
    await expect(sidebar).not.toContainText("Sales Orders");
  });

  test("Global Help Search and Context Help Button", async ({ page }) => {
    // 1. Login as Company E Admin (all modules active)
    await page.goto("/login");
    await page.fill("input[type='email'], input#email", "admin@company-e.com");
    await page.fill("input[type='password']", "Passw0rd@123");
    
    // Fill tenant slug
    const tenantInput = page.locator("input[name='tenant_slug'], input[placeholder*='tenant' i]");
    if (await tenantInput.count() > 0) {
      await tenantInput.fill("company-e");
    }
    
    await page.click("button[type='submit']");
    await page.waitForURL(/dashboard/, { timeout: 15000 });

    // 2. Test Context Help (?) Button in Header
    await page.goto("/leads");
    await page.waitForURL(/leads/, { timeout: 15000 });

    // Find and click 'Help' button in Header
    const helpBtn = page.locator("button:has-text('Help')");
    await expect(helpBtn).toBeVisible({ timeout: 15000 });
    await helpBtn.click();

    // Verify it redirect directly to CRM -> Lead Management article
    await page.waitForURL(/help\/lead-management/, { timeout: 15000 });
    await expect(page.locator("h1")).toHaveText("Lead Management Guide", { timeout: 15000 });

    // 3. Test Global Help Search (Ctrl+K overlay)
    const searchInput = page.locator("input[placeholder*='Search help']");
    await expect(searchInput).toBeVisible({ timeout: 15000 });
    await searchInput.fill("visits");
    
    // Wait for search dropdown overlay list to appear
    const searchResults = page.locator(".ant-card:has-text('Search Results')");
    await expect(searchResults).toBeVisible({ timeout: 15000 });
    await expect(searchResults).toContainText("Technician Site Visits");

    // Click search result to load article
    await page.click("text=Technician Site Visits");
    await page.waitForURL(/help\/engineer-visits/, { timeout: 15000 });
    await expect(page.locator("h1")).toHaveText("Technician Site Visits", { timeout: 15000 });
  });

});
