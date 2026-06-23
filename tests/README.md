# CCTV AMC & Service Management — Test Suite

This folder is the **canonical test root** for the entire platform.
It contains backend unit tests, backend integration tests, frontend unit tests,
and Playwright end-to-end tests, organised so they can be run independently or
as one CI pipeline.

**Status:** 312 backend tests + 60 frontend unit tests passing.
Backend integration coverage spans **all 21 API routers**; the Playwright E2E
specs cover the major browser flows (run against a live stack).

---

## Directory layout

```
tests/
├── README.md                 ← you are here
├── conftest.py               ← adds backend/ to sys.path (project-root level)
│
├── backend/
│   ├── conftest.py           ← shared async fixtures (SQLite in-memory, JWT, tenant/user/site)
│   ├── pytest.ini            ← asyncio_mode=auto, warning filters
│   │
│   ├── unit/                 ← pure-function / logic tests (no DB, fast)
│   │   ├── test_security.py
│   │   ├── test_gst.py
│   │   ├── test_payment_logic.py
│   │   ├── test_reports_export.py
│   │   ├── test_pm_schedule_logic.py
│   │   └── test_tenant_plan_limits.py
│   │
│   └── integration/          ← async API tests against an in-memory SQLite DB
│       ├── test_health.py            test_auth_flow.py     test_users.py
│       ├── test_tenants.py           test_customers.py     test_leads.py
│       ├── test_vendors.py           test_assets.py        test_quotations.py
│       ├── test_amc_contracts.py     test_service_tickets.py
│       ├── test_engineer_visits.py   test_inventory.py     test_sales_orders.py
│       ├── test_invoices.py          test_payments.py      test_notifications.py
│       ├── test_reports.py           test_documents.py     test_installations.py
│       └── test_portal.py
│
└── frontend/
    ├── unit/                 ← Vitest unit tests (Redux slices, utilities)
    │   ├── authSlice.test.ts
    │   ├── customerSlice.test.ts
    │   ├── ticketSlice.test.ts
    │   └── menuFilter.test.ts
    │
    └── e2e/                  ← Playwright browser E2E tests
        ├── playwright.config.ts
        ├── auth.spec.ts
        ├── customers.spec.ts
        ├── tickets.spec.ts
        ├── invoices.spec.ts
        └── portal.spec.ts
```

---

## Running the tests

### Backend — all tests (unit + integration), in-memory SQLite, no Postgres needed

```bash
cd tests/backend
../../backend/venv/bin/python -m pytest -q
```

Run a single layer:

```bash
../../backend/venv/bin/python -m pytest unit -q
../../backend/venv/bin/python -m pytest integration -q
```

With coverage:

```bash
../../backend/venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

> Integration tests run against `sqlite+aiosqlite:///:memory:`. PostgreSQL
> Row-Level Security is not exercised here; tenant isolation is still verified
> through the application-layer `TenantRepository` filtering and the portal
> cross-scope isolation tests. To run against real Postgres (and RLS), set
> `TEST_DATABASE_URL=postgresql+asyncpg://…` before invoking pytest.

### Frontend — unit tests (Vitest)

The Redux/utility unit tests in `tests/frontend/unit/` are wired into the
frontend Vitest config (`frontend/vitest.config.ts` `test.include`), so they run
directly alongside the co-located component tests — **no copying required**:

```bash
cd frontend
npm test            # vitest run  → 60 tests
```

### Frontend — E2E tests (Playwright)

E2E specs need the full stack running (backend at :8000, frontend at :5173) and
a seeded admin user. Override credentials via env vars
(`E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`, `E2E_TENANT_SLUG`).

```bash
cd tests/frontend/e2e
npm install @playwright/test
npx playwright install chromium
npx playwright test
```

---

## Coverage map (functionality → tests)

| Domain / API router        | Integration tests              |
|----------------------------|--------------------------------|
| Auth & sessions            | test_auth_flow                 |
| Tenants (platform admin)   | test_tenants                   |
| Users & RBAC               | test_users                     |
| Customers & contacts       | test_customers                 |
| Leads → conversion         | test_leads                     |
| Quotations                 | test_quotations                |
| Sales orders               | test_sales_orders              |
| AMC contracts & PM sched.  | test_amc_contracts             |
| Service tickets & SLA      | test_service_tickets           |
| Engineer visits (field)    | test_engineer_visits           |
| Installations & handover   | test_installations             |
| Assets (CCTV)              | test_assets                    |
| Inventory & stock          | test_inventory                 |
| Vendors & procurement      | test_vendors                   |
| Invoices & GST             | test_invoices                  |
| Payments & ageing          | test_payments                  |
| Documents                  | test_documents                 |
| Notifications              | test_notifications             |
| Reports & dashboard        | test_reports                   |
| Customer self-service portal | test_portal                  |

| Layer              | Status                          |
|--------------------|---------------------------------|
| Backend services   | Logic covered by unit suite     |
| Backend API routes | All 21 routers covered          |
| Frontend slices    | auth / customers / tickets      |
| E2E happy paths    | auth, customers, tickets, invoices, portal |
