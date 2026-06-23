# Phase 1 Requirement Traceability Matrix

Date: 2026-06-23 · Branch: `feat/phase1-gap-remediation`
Status legend: `Done` · `Backend only` (API/service present, no UI) · `UI missing` · `Partial` · `Not started` · `Needs hardening`

This matrix is the release checklist (plan Step 1). It is updated as each step lands.
Evidence paths are repo-relative.

## A. SRS functional areas

| # | Area | Status | Backend evidence | UI evidence | Gap / acceptance |
|---|---|---|---|---|---|
| 1 | Platform / tenant admin | **Done** | `api/v1/tenants.py`, `services/tenant.py`, `test_platform_admin.py` | `pages/platform/*` | ✅ Step 2: list/create/suspend/activate/cancel, usage, metrics, sub-invoices, UI + guard. Live-verified on Postgres+RLS. |
| 2 | Customer self-service portal | **Done** | `models/customer_portal_user.py`, mig `012`, `services/portal.py`, `api/v1/portal.py`, `test_customer_portal.py` | `pages/portal/*` | ✅ Step 3: separate identity (scope=portal), customer+tenant scoping, raise/track tickets, AMC/assets/invoices, responsive UI. Live-verified on Postgres+RLS. |
| 3 | User & RBAC admin | Backend only | `api/v1/users.py`, `models/rbac.py`, `core/permissions.py` | — | No users/roles UI. **Step 4.1** |
| 4 | Leads | Partial | `api/v1/leads.py` | `pages/LeadsPage.tsx` | Convert flow in UI; follow-up notif. |
| 5 | Customers & sites | Partial | `api/v1/customers.py` | `pages/CustomersPage.tsx` | Sites/contacts UI depth. |
| 6 | Vendors & procurement | Backend only | `api/v1/vendors.py`, `services/vendor.py` | — | No vendor/PO/payable UI. **Step 4.2** |
| 7 | Inventory & reorder | Backend only | `api/v1/inventory.py`, `services/inventory.py` | — | No inventory UI. **Step 4.3** |
| 8 | Quotations | Backend only | `api/v1/quotations.py` | — | No quotation UI. **Step 4.4** |
| 9 | Sales orders | Backend only | `api/v1/sales_orders.py` | — | No sales-order UI. **Step 4.4** |
| 10 | AMC contracts | Partial | `api/v1/amc.py`, `services/amc.py` | `pages/AMCPage.tsx` | Activate/PM schedule actions in UI. |
| 11 | PM schedules | Backend only | `services/pm_schedule.py`, `models/pm_schedule.py` | — | Surface PM schedule in AMC UI. |
| 12 | Installations & handover | Backend only | `api/v1/installations.py` | — | No installation UI + handover OTP. **Step 4.5** |
| 13 | Service tickets | Partial | `api/v1/service_tickets.py` | `pages/ServiceTicketsPage.tsx` | Assign/comments/visit history UI. |
| 14 | Engineer visits & media | Backend only | `api/v1/engineer_visits.py` | — | No visit UI. **Step 4.6** |
| 15 | Assets & warranties | Backend only | `api/v1/assets.py`, `api/v1/documents.py` | — | No asset/document UI. **Step 4.7** |
| 16 | Invoicing (GST) | Partial | `api/v1/invoices.py`, `services/gst.py`, `services/invoice.py` | `pages/InvoicesPage.tsx` | Verified by `test_invoice_gst.py`. |
| 17 | Payments | Partial | `api/v1/payments.py` | `pages/PaymentsPage.tsx` | — |
| 18 | Documents & storage | Backend only | `api/v1/documents.py`, `services/storage.py` | — | No document UI. **Step 4.7** |
| 19 | Notifications & templates | Partial | `services/notification.py`, `notification_events.py` | — | Only 4/10 events wired; no in-app center. **Step 7** |
| 20 | Reports & exports | Backend only | `api/v1/reports.py`, `services/reports.py` | — | 6 reports, no UI; add missing. **Step 5** |
| 21 | Dashboards | Partial | `reports.dashboard_kpis` | `pages/DashboardPage.tsx` | Role-aware dashboards. **Step 5** |

## B. TAD cross-cutting requirements

| # | Requirement | Status | Evidence | Gap |
|---|---|---|---|---|
| C1 | RBAC enforcement | Partial | `core/deps.py`, `core/permissions.py` | Route-by-route authz audit. **Step 8** |
| C2 | Tenant isolation (app + RLS) | Done | `models/base.py`, `repositories/base.py`, `test_rls_postgres.py`, `test_tenant_isolation.py` | Customer-scope layer pending (**Step 3/8**) |
| C3 | Audit chain | Done | `services/audit.py`, `test_audit_log.py` | Confirm coverage on all mutations. **Step 8** |
| C4 | Notification engine | Partial | `services/notification.py` | Event wiring + retries. **Step 7** |
| C5 | Reporting | Backend only | `services/reports.py` | Expand + UI. **Step 5** |
| C6 | Offline mobile sync | Needs hardening | `mobile/src/services/syncManager.ts` | LWW → conflict detection; sync status UI. **Step 6** |
| C7 | Secure mobile storage | Needs hardening | `mobile/src/services/apiClient.ts` (AsyncStorage) | Keychain/Keystore. **Step 6** |
| C8 | Object storage isolation | Partial | `services/storage.py` | Tenant-prefix verification. **Step 8** |
| C9 | Monitoring | Partial | Prometheus instrumentator, Sentry in `main.py` | — |
| C10 | CI/CD | Partial | `.github/workflows` | Add FE/mobile test stages. **Step 9** |
| C11 | Deployment config | Partial | `infra/`, `.env.example` | Env-specific CORS/providers. **Step 8** |

## C. Test coverage status

| Layer | Status | Evidence |
|---|---|---|
| Backend integration | Done | `backend/tests/integration/*` (33 passing) |
| Backend unit | Partial | `backend/tests/unit/*` |
| Frontend | Not started | none — harness gap (**Step 9**) |
| Mobile | Not started | none (**Step 9**) |
| E2E | Not started | none (**Step 9/10**) |

## Execution order (this engagement)

Step 0 ✅ → Step 1 ✅ → Step 2 (platform admin) → Step 4 (office modules) →
Step 3 (customer portal*) → Step 5 (reports) → Step 7 (notifications) →
Step 6 (mobile) → Step 8 (security) → Step 9 (tests) → Step 10 (acceptance).

\* Step 3 customer-portal authentication is the one flagged architectural decision
  (plan §8.2); to be confirmed with stakeholders before its identity model is built.
