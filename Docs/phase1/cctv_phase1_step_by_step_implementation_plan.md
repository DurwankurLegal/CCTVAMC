# CCTV AMC SaaS Phase 1 Step-by-Step Implementation Plan

Date: 23 June 2026  
Source: `outputs/cctv_phase1_review_report.docx`  
Objective: Close the Phase 1 gaps identified in the review report and reach a demonstrable sign-off state.

## 1. Delivery Principles

1. Treat this as a gap-fix release, not a rewrite.
2. Keep the backend foundation that is already working: tenant isolation, RLS, audit chain, enum constraints, installation/PM workflow, notification engine, document storage, and backend integration tests.
3. Prioritize user-facing completeness first, because most remaining gaps are product workflow gaps rather than missing database foundations.
4. Every feature must finish with a testable acceptance path: API, UI, tenant isolation, RBAC, audit behavior, and export/report evidence where relevant.
5. Do not call Phase 1 complete until the customer portal, platform admin console, missing office modules, reporting surface, mobile hardening, and regression suite are demonstrated end-to-end.

## 2. Workstream Summary

| Workstream | Priority | Primary Outcome |
|---|---:|---|
| Scope and traceability | Critical | Clear Phase 1 requirement matrix with owners, status, and test method |
| Platform admin console | High | Durwankur can onboard tenants and manage subscription billing through UI |
| Customer self-service portal | Critical | Customers can raise/view tickets and view relevant service/AMC status |
| Office web module completion | High | Tenant staff can run all documented workflows from browser UI |
| Reporting and notifications | High | Management reports, exports, dashboards, templates, and event flows are usable |
| Mobile security and sync hardening | Medium | Technician app uses secure token storage and reliable offline reconciliation |
| QA, release, and production readiness | High | Repeatable sign-off suite proves business flow, security, and stability |

## 3. Step-by-Step Plan

### Step 0: Prepare the Delivery Baseline

Goal: Create a controlled baseline before feature work starts.

Actions:

1. Create a delivery branch for Phase 1 gap closure.
2. Run current backend test suite and record the baseline result.
3. Run frontend build and lint, even if no tests exist yet, to establish current UI health.
4. Run mobile TypeScript/build checks where the local setup allows.
5. Confirm local environment can start backend, frontend, Redis, Postgres, and Celery.
6. Capture current OpenAPI schema from FastAPI as the API contract baseline.
7. Confirm seeded data includes at least two tenants, platform admin, tenant admin, technician, billing user, and sample customer.

Acceptance criteria:

1. Baseline test/build results are recorded.
2. Known failures are documented separately from new implementation work.
3. Team agrees that future defects are compared against this baseline.

Suggested owner: Technical Lead  

### Step 1: Build the Requirement Traceability Matrix

Goal: Convert the SRS/TAD and review report into a working delivery matrix.

Actions:

1. List all 21 SRS functional areas.
2. Add TAD cross-cutting requirements: RBAC, tenant isolation, audit, notification engine, reporting, offline mobile, storage, monitoring, CI/CD, and deployment.
3. For each item, assign one of these statuses: `Done`, `Backend only`, `UI missing`, `Partial`, `Not started`, `Needs hardening`.
4. Add source references for current code evidence, such as backend router, service, model, frontend page, mobile screen, or test file.
5. Add one owner per item.
6. Add one acceptance test per item.
7. Use the matrix as the release checklist and update it daily.

Acceptance criteria:

1. Every in-scope Phase 1 requirement has owner, status, evidence, gap, and acceptance method.
2. No feature work is accepted without updating the matrix.

Suggested owner: Solution Architect plus QA Lead  

### Step 2: Complete Platform Admin Console

Goal: Make platform tenant administration usable without direct API calls.

Backend checks:

1. Verify tenant APIs support list, create, view, update, suspend, activate, cancel, and subscription invoice generation.
2. Confirm plan limits are enforced for users, sites, and technicians.
3. Confirm platform admin access is enforced with platform-level RBAC.
4. Add missing endpoints if needed for tenant dashboard metrics, subscription invoice status, and tenant usage summary.
5. Add audit entries for tenant changes and subscription invoice actions.

Frontend actions:

1. Add a platform-admin route group.
2. Add tenant list page with search, status filter, plan filter, and create tenant action.
3. Add tenant detail page with profile, billing, status, plan, usage limits, users, and recent activity.
4. Add subscription invoice screen with generate invoice and invoice history.
5. Add platform dashboard with tenant count, active/suspended tenants, plan distribution, and recent tenant activity.
6. Add route guards so only platform admins can see platform screens.

Tests:

1. Backend tests for platform admin allowed and tenant admin denied.
2. Frontend tests for route visibility and tenant form validation.
3. API integration test for subscription invoice generation.
4. Tenant isolation regression test after platform admin changes.

Acceptance criteria:

1. Platform admin can onboard a tenant through UI.
2. Platform admin can update tenant plan/status through UI.
3. Platform admin can generate and view subscription invoices through UI.
4. Tenant users cannot access platform admin routes or APIs.

Suggested owner: Frontend Lead plus Backend Lead  

### Step 3: Implement Customer Self-Service Portal

Goal: Deliver the missing customer-facing interface required by the SRS.

Scope decision:

1. Use the existing React app with a separate route group unless a separate build is explicitly required.
2. Keep customer portal permissions separate from tenant staff permissions.

Backend actions:

1. Define customer portal identity model: customer admin user, linked customer, tenant, email/phone, status, and allowed actions.
2. Add customer portal authentication or extend current user model with a customer-scoped role.
3. Add endpoints for customer-visible profile, sites, AMC contracts, assets, tickets, ticket comments, ticket creation, documents, and invoices if required.
4. Enforce customer-level scoping in addition to tenant scoping.
5. Add audit logs for customer-created tickets and customer comments.
6. Add notification events for ticket creation, ticket status updates, and customer replies.

Frontend actions:

1. Add customer portal login.
2. Add customer dashboard with open tickets, AMC status, upcoming visits, and recent notifications.
3. Add raise ticket flow with site, asset, priority, complaint, optional attachments.
4. Add ticket detail view with status, comments, visit history, and closure notes.
5. Add AMC/asset view showing contract validity and covered assets.
6. Add invoice/payment visibility if included in Phase 1.
7. Ensure customer portal is responsive on mobile browser.

Tests:

1. Backend tests proving customer A cannot view customer B data inside the same tenant.
2. Backend tests proving customer portal user cannot access tenant staff APIs.
3. Frontend tests for login, raise ticket, ticket detail, and unauthorized route handling.
4. End-to-end test for customer raises ticket and tenant staff sees it.

Acceptance criteria:

1. Customer can log in and raise a ticket.
2. Customer can view only their own tickets, sites, assets, AMC, and documents.
3. Tenant staff receives notification for customer-created ticket.
4. Customer portal works on desktop and mobile browser.

Suggested owner: Full-stack Feature Team  

### Step 4: Complete Missing Tenant Office Web Modules

Goal: Surface existing backend capabilities in the tenant back-office UI.

Recommended implementation order:

1. User and RBAC administration.
2. Vendors and procurement.
3. Inventory and reorder workflow.
4. Quotations and sales orders.
5. Installations and handover.
6. Engineer visits and media.
7. Documents and warranties.
8. Notifications and templates.
9. Reports and exports.

Actions for each module:

1. Add route and menu entry with RBAC-driven visibility.
2. Add list page with search, filter, pagination, and status tags.
3. Add create/edit forms using the existing Ant Design pattern.
4. Add detail view for workflow-heavy modules such as installations, tickets, visits, and quotations.
5. Add action buttons for state transitions, such as approve quote, activate AMC, request handover OTP, complete visit, reorder stock, mark notification read.
6. Add consistent error handling, loading state, empty state, and permission-denied state.
7. Wire all pages through the shared API client.
8. Add frontend tests for form validation, route access, and core action flows.

Module-specific acceptance criteria:

1. User/RBAC: Tenant admin can create users, assign roles, and verify module visibility changes.
2. Vendors/procurement: User can create vendor, create purchase order, record vendor payment, and view payable balance.
3. Inventory: User can create item, adjust stock, view low-stock items, and trigger reorder.
4. Quotations/sales orders: User can create quotation, approve/reject, convert to AMC or sales order, and view status history.
5. Installations: User can create work order, record survey, update progress, request handover OTP, and complete handover.
6. Engineer visits: User can schedule visit, assign technician, view check-in/check-out, view photos/signature, and see parts used.
7. Documents/warranties: User can upload/list documents against customer/site/asset/visit/invoice and view warranty metadata.
8. Notifications: Admin can manage templates, user can view in-app notifications, and notification logs are visible to authorized users.
9. Reports: User can run standard reports, apply filters, and export CSV/XLSX/PDF.

Suggested owner: Frontend Lead with Backend support  
Suggested duration: 15 to 25 days depending on team size

### Step 5: Expand Reporting and Dashboards

Goal: Bring management reporting closer to the SRS/TAD expectations.

Backend actions:

1. Confirm existing report endpoints: dashboard, SLA, lead conversion, revenue by customer, technician productivity, inventory consumption.
2. Add missing reports for AMC renewal pipeline, overdue receivables, payment collection, ticket turnaround, technician workload, inventory valuation, purchase orders, installation pipeline, and customer service history.
3. Add common report query model: date range, customer, site, technician, status, priority, category, export format.
4. Add report execution audit log or export log.
5. Ensure heavy report queries are ready for read replica usage when deployed.
6. Ensure XLSX/PDF exports include tenant branding and Indian currency/date formatting.

Frontend actions:

1. Add reports landing page with report categories.
2. Add report runner with filters and export actions.
3. Add role-aware dashboards for tenant admin, operations manager, sales, accounts, and service coordinator.
4. Add visual summaries only where they help operations: SLA compliance, AMC renewal pipeline, receivables, tickets by priority, technician productivity.

Tests:

1. Backend tests for every report key.
2. Export tests for CSV, XLSX, and PDF.
3. Frontend tests for filters, export actions, and empty states.
4. Performance test for large report datasets.

Acceptance criteria:

1. Every report named in the Phase 1 scope is available from UI.
2. Reports support date and domain filters.
3. Exports are generated without manual database access.
4. Report access respects tenant and role boundaries.

Suggested owner: Backend Lead plus Frontend Lead  

### Step 6: Harden Mobile Security and Offline Sync

Goal: Align the technician app with the architecture requirements for secure storage and reliable offline operation.

Security actions:

1. Replace `AsyncStorage` token storage with Keychain/Keystore-backed secure storage.
2. Store refresh tokens securely and minimize access token lifetime.
3. Add logout token cleanup using secure storage.
4. Add optional device/session revocation support if required for Phase 1.
5. Review whether certificate pinning is required before production release.

Offline sync actions:

1. Add a sync status screen showing pending, synced, failed, and retrying items.
2. Add retry count, last error, and last attempted timestamp to the local sync queue.
3. Replace blind last-write-wins with explicit conflict detection using server timestamps or version numbers.
4. Add conflict resolution behavior for visit checkout, parts used, media upload, and signature upload.
5. Ensure locally created visits receive server IDs and subsequent queued actions are remapped correctly.
6. Ensure media upload failures remain visible and retryable.

Backend actions:

1. Add or formalize a `/mobile/sync` batch endpoint if single-action sync is not enough.
2. Add idempotency keys for mobile sync writes.
3. Add server-side validation for technician assignment and tenant scope.
4. Add audit entries for offline-originated actions.

Tests:

1. Mobile unit tests for secure token service.
2. Mobile tests for queue retry behavior.
3. Backend tests for idempotent mobile sync.
4. End-to-end test for offline check-in, photo capture, checkout, reconnect, and server reconciliation.

Acceptance criteria:

1. Tokens are not stored in AsyncStorage.
2. Technician can work offline and see pending sync state.
3. Reconnect sync is idempotent and visible.
4. Failed sync items are not silently lost.

Suggested owner: Mobile Lead plus Backend Lead  

### Step 7: Complete Notification Event Wiring

Goal: Ensure notification templates and logs are connected to real business events.

Actions:

1. Confirm implemented events: ticket assignment, SLA breach, AMC expiry, payment due.
2. Add missing event calls for lead follow-up, quote sent, quote approval/rejection, installation handover, visit reminder, warranty expiry, low stock, purchase order creation, ticket status updates, and customer ticket comments.
3. Add template seed data per tenant.
4. Add in-app notification center UI for internal users.
5. Add notification preferences where required.
6. Replace placeholder SMS provider URL before production.
7. Add delivery failure visibility and retry controls for authorized users.

Tests:

1. Event-specific backend tests proving log rows are created.
2. Worker tests for success/failure paths.
3. UI tests for template CRUD and notification read/unread behavior.

Acceptance criteria:

1. Important business events create notifications automatically.
2. Templates are configurable per tenant.
3. Failed notifications are visible and retryable.

Suggested owner: Backend Lead plus Frontend Lead  

### Step 8: Strengthen RBAC, Security, and Compliance

Goal: Close the remaining production-readiness risk around access, secrets, and compliance.

Actions:

1. Review every backend route and decide whether it needs `get_current_user`, `require_permission`, or `require_platform_admin`.
2. Add read permissions where read access should not be available to every authenticated user.
3. Verify all mutations write audit logs through repository or explicit audit service.
4. Ensure customer portal introduces customer-scope checks, not just tenant-scope checks.
5. Confirm object storage keys are tenant-prefixed and downloads do not expose cross-tenant files.
6. Replace any placeholder provider URLs or fake delivery behavior before production.
7. Ensure CORS is environment-specific and not overly broad.
8. Confirm secrets are only loaded from environment/secret store.
9. Verify GST, INR formatting, Indian date format, and timezone behavior in invoices, reports, and exports.

Tests:

1. Route authorization matrix test for high-risk modules.
2. Cross-tenant API tests for every module.
3. Customer-level isolation tests.
4. Audit coverage tests for representative mutations.
5. Object storage access tests for tenant isolation.

Acceptance criteria:

1. Unauthorized users receive `403` or `404` consistently.
2. No cross-tenant or cross-customer data access path is found.
3. Audit chain remains valid after full workflow testing.

Suggested owner: Security-minded Backend Engineer plus QA Lead  

### Step 9: Add Frontend and Mobile Test Coverage

Goal: Remove the UI regression blind spot called out in the review.

Frontend test setup:

1. Add test setup for React Testing Library and Ant Design.
2. Add API mocking strategy.
3. Add route guard tests.
4. Add smoke tests for each page.
5. Add form validation tests for customer, ticket, AMC, invoice, payment, vendor, inventory, quotation, installation, and user forms.

Mobile test setup:

1. Add tests for login and secure token storage.
2. Add tests for ticket list and visit detail flow.
3. Add tests for offline queue creation and retry behavior.
4. Add tests for media upload queue state.

End-to-end test setup:

1. Add a browser E2E suite for platform admin onboarding.
2. Add customer portal ticket creation E2E.
3. Add tenant staff ticket assignment and visit completion E2E.
4. Add invoice/payment/report export E2E.

Acceptance criteria:

1. Frontend tests run in CI.
2. Mobile tests run in CI or documented mobile test pipeline.
3. Critical flows are protected by repeatable end-to-end tests.

Suggested owner: QA Lead plus Frontend/Mobile Leads  

### Step 10: Perform End-to-End Phase 1 Acceptance Run

Goal: Prove Phase 1 readiness with scripted demonstrations and test evidence.

Acceptance scenario sequence:

1. Platform admin creates a new tenant.
2. Tenant admin configures tenant profile, users, roles, and notification templates.
3. Sales user creates lead and converts it to customer.
4. Tenant user creates quotation and approves it.
5. Installation work order is created, surveyed, executed, and handed over.
6. AMC contract is created/activated and PM schedule is generated.
7. Customer portal user raises a service ticket.
8. Service coordinator assigns ticket to technician.
9. Technician completes mobile check-in, media capture, checkout, parts usage, and signature.
10. Inventory is adjusted and low-stock reorder is triggered.
11. Invoice is generated with GST logic and payment is recorded.
12. Notifications fire for assignment, SLA/expiry/payment events as applicable.
13. Management report is run and exported.
14. Audit chain is verified.
15. Tenant isolation tests are run across at least two tenants.

Exit criteria:

1. All critical and high findings from the review report are closed.
2. All acceptance scenarios pass.
3. No critical security defect remains open.
4. No cross-tenant or cross-customer data leak is found.
5. UI test, backend test, and E2E test evidence is attached to the release sign-off.

Suggested owner: QA Lead plus Solution Architect  

## 4. Suggested Sprint Breakdown

| Sprint | Focus | Expected Output |
|---|---|---|
| Sprint 0 | Baseline, traceability, architecture decisions | Delivery matrix, baseline test result, confirmed scope |
| Sprint 1 | Platform admin and customer portal backend foundation | Admin UI skeleton, customer identity/scoping APIs |
| Sprint 2 | Customer portal UI and office missing modules part 1 | Customer portal, user/RBAC, vendors, inventory |
| Sprint 3 | Office missing modules part 2 | Quotations, sales orders, installations, engineer visits, documents |
| Sprint 4 | Reports, notifications, mobile hardening | Reports UI/export, event wiring, secure mobile tokens, sync status |
| Sprint 5 | QA hardening and sign-off | E2E suite, performance checks, acceptance run, release evidence |

## 5. Parallelization Plan

Recommended parallel tracks:

1. Backend track: customer portal identity, report expansion, notification wiring, RBAC hardening, mobile sync APIs.
2. Frontend track: platform admin, customer portal, missing office modules, reports UI.
3. Mobile track: secure storage, sync queue status, conflict handling, media reconciliation.
4. QA track: traceability matrix, API regression, frontend/mobile test harness, E2E acceptance suite.
5. DevOps track: CI updates, monitoring checks, environment config, provider/secret validation.

Dependency notes:

1. Customer portal UI depends on customer portal identity and customer-scoped APIs.
2. Reports UI depends on expanded report API and export contracts.
3. Mobile sync hardening depends on idempotent server behavior if batch sync is introduced.
4. E2E acceptance depends on seed data and stable test users across at least two tenants.

## 6. Definition of Done

A task is done only when:

1. Code is implemented and merged to the delivery branch.
2. Relevant backend, frontend, mobile, or E2E tests are added or updated.
3. RBAC behavior is verified.
4. Tenant isolation behavior is verified where data is tenant-owned.
5. Audit behavior is verified for state-changing actions.
6. UI includes loading, empty, error, and permission-denied states.
7. The requirement traceability matrix is updated.
8. QA has a reproducible acceptance path.

## 7. Phase 1 Sign-Off Checklist

| Area | Sign-off Question |
|---|---|
| Platform admin | Can Durwankur onboard and manage tenants from UI? |
| Customer portal | Can a customer raise and track service requests without tenant staff assistance? |
| Tenant back office | Can staff complete sales, service, AMC, inventory, billing, and reporting workflows from UI? |
| Mobile | Can a technician work offline and sync reliably with secure token storage? |
| Reporting | Can management run and export the required reports? |
| Notifications | Are key events automatically notifying the right users/channels? |
| Security | Are RBAC, tenant isolation, customer isolation, audit, and storage isolation verified? |
| QA | Are backend, frontend, mobile, and E2E tests running repeatably? |
| Release readiness | Are environment config, providers, monitoring, and rollback checks ready? |

## 8. Immediate Next Actions

1. Create the requirement traceability matrix.
2. Confirm customer portal authentication approach.
3. Start platform admin UI and customer portal API work in parallel.
4. Add frontend/mobile test harness before large UI expansion.
5. Schedule a Phase 1 acceptance rehearsal using the scenario list in Step 10.
