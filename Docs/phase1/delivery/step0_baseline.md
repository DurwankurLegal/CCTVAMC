# Phase 1 Gap Remediation — Step 0 Delivery Baseline

Date captured: 2026-06-23
Branch: `feat/phase1-gap-remediation`
Captured by: Delivery execution (automated)

This is the controlled baseline taken **before** any Phase 1 gap-closure feature work.
All future defects are to be compared against this record (plan Step 0, acceptance #3).

## 1. Repository layout

| Area | Path | State |
|---|---|---|
| Backend (FastAPI) | `backend/app` | Broad — 20 API routers, full model/service/repository layers |
| Frontend (React/AntD) | `frontend/src` | Thin — 8 pages, no platform-admin / customer portal / most office modules |
| Mobile (React Native) | `mobile/src` | Minimal — login, ticket list, visit detail, sync manager |
| Infra | `infra/` | Docker compose, etc. |

## 2. Test / build baseline

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend && venv/bin/python -m pytest` | **33 passed, 1 skipped** (~18s) |
| Frontend types | `cd frontend && npx tsc --noEmit` | **Pass (clean)** |
| Frontend lint | `cd frontend && npm run lint` | **FAIL — no `eslint.config.js`** (ESLint v9 needs flat config) |
| Frontend unit tests | `cd frontend && npm test` | **None — no jest config, no test files** |
| Mobile typecheck | n/a locally | Not run (no local RN toolchain verified) |

> Note: backend `venv` runs Python 3.9.6 locally though the project targets 3.12.
> Tests pass on 3.9; production/CI uses 3.12. Recorded as an environment observation, not a defect.

## 3. Known pre-existing gaps (NOT introduced by this work)

1. Frontend has **no ESLint flat config** → `npm run lint` cannot run.
2. Frontend has **no test harness** (jest referenced in `package.json`, but no config/tests).
3. Mobile stores JWTs in **`AsyncStorage`** (`mobile/src/screens/LoginScreen.tsx`,
   `mobile/src/services/apiClient.ts`) — must move to secure storage (plan Step 6).
4. Seed data (`backend/scripts/seed.py`) creates **only 1 tenant + 1 admin** — missing
   the platform admin, a 2nd tenant, and technician/billing/customer users required by
   the Step 0 acceptance criteria and the Step 10 acceptance run.
5. Notification engine: **10 event constants defined**, but only **4 wired** to real
   business events (`TICKET_ASSIGNED`, `AMC_EXPIRY`, `SLA_BREACH`, `PAYMENT_DUE`).
6. Reporting: **6 report producers** exist (`dashboard`, `sla`, `lead-conversion`,
   `revenue-by-customer`, `technician-productivity`, `inventory-consumption`) vs. the
   ~15 named in the plan (Step 5).

## 4. Backend foundation confirmed working (keep, do not rewrite)

- Tenant isolation via `TenantMixin` + repository base + PostgreSQL RLS (`SET LOCAL app.tenant_id`).
- RBAC: `get_current_user`, `require_roles`, `require_permission`, `require_platform_admin`
  in `backend/app/core/deps.py`; default role→permission matrix in `core/permissions.py`;
  custom DB roles in `models/rbac.py`.
- Audit log with SHA-256 hash chaining.
- Platform/tenant separation: `User.is_platform_admin`, `Tenant.status`, `PLAN_LIMITS`,
  `enforce_limit()`, subscription invoicing.
- Backend integration tests across auth, RLS, isolation, RBAC, invoices/GST, reports, etc.

## 5. Acceptance (Step 0)

- [x] Baseline test/build results recorded (this document).
- [x] Known failures documented separately from new implementation work (§3).
- [x] Baseline is the comparison point for future defects.
