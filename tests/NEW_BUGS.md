# E2E Test Run — New Findings & Bug Report (2026-06-24)

This document lists the newly identified application and test-suite bugs uncovered during our E2E Playwright test run and visual manual checks.

---

## 1. Application-Code Defect Summary

### 🟠 BUG-06 — Empty Customer Dropdowns on Direct Page Navigation/Reload (AMC & Tickets Pages)

- **Where:** 
  - `frontend/src/pages/AMCPage.tsx`
  - `frontend/src/pages/ServiceTicketsPage.tsx`
- **Problem:** Both pages read the list of customers from the Redux store (`const customers = useSelector((s: RootState) => s.customers.items)`), but they do not dispatch the `fetchCustomers` thunk in their `useEffect` hooks. If a user navigates directly to `/amc` or `/tickets` (or refreshes the page on these paths), the customers slice is empty, resulting in an empty dropdown when trying to create an AMC or raise a ticket. The list is only populated if the user visits the `/customers` page first in their session.
- **Impact:** Medium/High. Users cannot create new AMC contracts or raise tickets if they refresh the page or navigate directly. This also causes isolated E2E tests targeting these pages to fail or time out because the dropdowns are empty.
- **Recommended Fix:** Import `fetchCustomers` from `../store/customerSlice` and dispatch it inside the `useEffect` block of both pages:
  ```typescript
  useEffect(() => {
    dispatch(fetchTickets());
    dispatch(fetchCustomers());
  }, [dispatch]);
  ```

---

### 🟠 BUG-07 — Technician Role Rejection Crashes Reference Data Loading in Engineer Visits Page

- **Where:** `frontend/src/pages/EngineerVisitsPage.tsx` (`loadDropdowns`)
- **Problem:** The `loadDropdowns` function uses a single `Promise.all` to load `/users`, `/service-tickets`, and `/amc`. When a user with the `technician` role visits this page, the requests to `/users` and `/amc` fail with `403 Forbidden` (as technicians do not have read permissions for users or AMC contracts). This causes the entire `Promise.all` to reject immediately, aborting the loading of service tickets (even though technicians have `"service_tickets:read"` permission).
- **Impact:** Medium. For technicians, the tickets list fails to load. As a result, the technician dropdown is empty, and tickets are displayed with their raw UUIDs instead of friendly numbers in the visits table. The dropdowns fail silently due to an empty catch block.
- **Recommended Fix:** Separate the reference requests into individual `try/catch` blocks or use `Promise.allSettled` to let successful requests load independently:
  ```typescript
  const loadDropdowns = useCallback(async () => {
    // Load users (requires users:read/write)
    apiClient.get("/users", { params: { limit: 200 } })
      .then(res => setTechnicians(res.data.filter((u: Technician) => u.role === "technician")))
      .catch(() => {});

    // Load tickets (requires service_tickets:read)
    apiClient.get("/service-tickets", { params: { limit: 200 } })
      .then(res => setTickets(res.data))
      .catch(() => {});

    // Load AMC contracts (requires amc:read)
    apiClient.get("/amc", { params: { limit: 200 } })
      .then(res => setAmcContracts(res.data))
      .catch(() => {});
  }, []);
  ```

---

### 🟠 BUG-08 — Overdue Invoices and Defaulted Count is Always Zero on Dashboard & Invoices Ledger

- **Where:** 
  - `frontend/src/pages/InvoicesPage.tsx`
  - `frontend/src/pages/DashboardPage.tsx`
- **Problem:** Both pages filter overdue invoices by checking `item.status === "overdue"`. However, `"overdue"` is not a valid status value in the database/backend `InvoiceStatus` enum (which only has `draft`, `issued`, `paid`, `partially_paid`, `cancelled`, and `credit_note`). Unpaid invoices that are past their due date retain their status as `issued` or `partially_paid`.
- **Impact:** Medium. The operational dashboard incorrectly shows 0 overdue invoices and 0 defaulted invoices, and the "Outstanding Receivables" card on the invoices ledger displays 0 overdue invoices. The "defaulter" filter on the Invoices page also filters out all invoices, returning an empty table.
- **Recommended Fix:** Calculate the overdue status dynamically based on whether the invoice is unpaid (`issued` or `partially_paid`) and the due date is in the past:
  ```typescript
  const isOverdue = (item.status === "issued" || item.status === "partially_paid") && overdueDays(item) > 0;
  ```

---

### 🟡 BUG-09 — Missing Client-Side Email Validation on Leads Form

- **Where:** `frontend/src/pages/LeadsPage.tsx`
- **Problem:** The email input field uses a standard `<Input type="email" />` with no Ant Design form rule. This allows invalid email formats to be submitted, hitting the backend and throwing a 422 error which is displayed as a generic "Save failed" toast.
- **Impact:** Low. Poor UX on lead submission.
- **Recommended Fix:** Add an Ant Design email validation rule:
  ```typescript
  <Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Enter a valid email' }]}>
    <Input />
  </Form.Item>
  ```

---

## 2. Test-Suite Defect Summary

### 🔴 BUG-10 — Invalid Selector Syntax in Playwright Test Suite (False Negatives & Timeouts)

- **Where:** 
  - `tests/frontend/e2e/auth.spec.ts`
  - `tests/frontend/e2e/customers.spec.ts`
  - `tests/frontend/e2e/invoices.spec.ts`
  - `tests/frontend/e2e/portal.spec.ts`
  - `tests/frontend/e2e/tickets.spec.ts`
- **Problem:** The E2E tests mix Playwright's custom text selector engine syntax (`text=`) with CSS selectors inside comma-separated selector lists. When Playwright parses a selector starting with `text=`, it treats the entire rest of the string as the text content to match, looking for the literal text `"Invalid, text=credentials, .ant-message-error, [role='alert']"`.
- **Impact:** High. This causes 26 test cases to fail or time out because they search for non-existent text strings instead of selecting elements correctly.
- **Examples:**
  - `auth.spec.ts`: `page.locator("text=Invalid, text=credentials, .ant-message-error, [role='alert']")`
  - `customers.spec.ts`: `page.locator("text=Something went wrong, text=Error")`
- **Recommended Fix:** Split the selectors into proper Playwright locator checks, or use native CSS selectors like `.ant-alert-error` or `.ant-message-error`.

---

### 🟠 BUG-11 — Service Tickets Create Test Mismatched Button Click Target

- **Where:** `tests/frontend/e2e/tickets.spec.ts`
- **Problem:** The test tries to click a button with text `New`, `Create`, or `Add`. However, the actual button in the UI for raising tickets is labeled "Raise Ticket".
- **Impact:** High. The test times out waiting for a matching button.
- **Recommended Fix:** Update the click locator to target `"button:has-text('Raise Ticket')"`:
  ```typescript
  await page.click("button:has-text('Raise Ticket')");
  ```
