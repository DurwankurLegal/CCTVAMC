# Phase 1 Gap Remediation — Execution Summary

Date: 2026-06-23 · Branch: `feat/phase1-gap-remediation`

## Step completion

| Step | Workstream | Status |
|---|---|---|
| 0 | Delivery baseline | ✅ Complete |
| 1 | Requirement traceability matrix | ✅ Complete |
| 2 | Platform admin console | ✅ Complete (live-verified) |
| 3 | Customer self-service portal | ✅ Complete (live-verified) |
| 4 | Tenant office web modules (4.1–4.9) | ✅ Complete (live-verified) |
| 5 | Reporting & dashboards | ✅ Complete (live-verified) |
| 6 | Mobile security & offline sync | ✅ Complete — code (mobile toolchain not runnable here) |
| 7 | Notification event wiring + in-app center | ✅ Complete (live-verified) |
| 8 | RBAC / security / compliance hardening | ✅ Complete |
| 9 | Frontend/mobile/E2E test coverage | 🟡 Harness established; coverage to expand |
| 10 | End-to-end acceptance run | 🟡 Components verified piecemeal; formal scripted run pending |

## Test/build state at handoff

- Backend: **54 passed, 1 skipped** (baseline was 33) — `cd backend && venv/bin/python -m pytest`
- Frontend unit: **7 passed** (Vitest) — `cd frontend && npm test`
- Frontend types/build: clean — `npx tsc --noEmit && npm run build`

## New backend tests added

`test_platform_admin`, `test_customer_portal`, `test_user_admin`,
`test_notification_events`, `test_authorization_matrix`, `test_model_column_types`,
plus expanded `test_reports`.

## Bugs found & fixed via live verification (invisible to SQLite tests)

1. `quotations.valid_until` mapped as `String` vs `DATE` column → 500 on PostgreSQL. Fixed + added `test_model_column_types` guard.
2. Report PDF export raised unhandled 500 when weasyprint native libs absent → now a clean 503; CSV/XLSX unaffected.
3. Notification templates used `{var}` but the engine renders `{{var}}` → placeholders weren't substituted. Aligned seed + UI hint.
4. Hardcoded placeholder SMS provider URL (`sms.example.com`) → moved to `SMS_PROVIDER_URL` config, skip-with-warning when unset.

## New surfaces

- **Platform admin:** `/platform`, `/platform/tenants`, `/platform/tenants/:id`
- **Customer portal:** `/portal/*` (separate identity + token, `scope=portal`)
- **Office modules:** Users & Roles, Vendors, Inventory, Quotations & Sales Orders,
  Installations, Engineer Visits, Assets & Warranties, Notifications, Reports
- **In-app notification bell** (header) with unread badge + mark-read

## Remaining for full sign-off (Steps 9–10)

1. Expand frontend tests (route guards, per-form validation) and add mobile unit
   tests (secure token, queue retry) + a browser E2E suite.
2. Backend idempotency endpoint for mobile sync writes (headers already sent).
3. Execute the scripted Step 10 acceptance run across two tenants and attach evidence.
4. Pre-prod: provision weasyprint native libs (PDF), real SMS/WhatsApp providers,
   S3 credentials, environment-specific CORS origins.

## Phase 1 readiness

- **Ready for QA:** platform admin, customer portal, all office modules, reporting,
  notifications, security authorization.
- **Ready for UAT after:** Step 9 coverage expansion + Step 10 scripted acceptance run.
