# Plan: CCTV AMC → Multi-Company SaaS (sales-led, no billing)

> Status: Plan only — not yet implemented.
> Date: 2026-06-24
> Model: sales-led (platform admin provisions each company). No public signup. No payment gateway.

## Context: what already exists (verified in code)

This project is **already architected as multi-tenant** — this plan closes the gaps between
"multi-tenant foundation" and "production-grade multi-company SaaS," it does **not** retrofit tenancy.

| Capability | Status | Where |
|---|---|---|
| Tenant model w/ plans, status, branding, settings, billing fields | Done | `backend/app/models/tenant.py` |
| Tenant isolation: app-layer `tenant_id` filter **+** Postgres RLS (`set_config('app.tenant_id')`) | Done | `backend/app/repositories/base.py` |
| Platform-admin console APIs (list/create/suspend/activate/cancel, metrics, usage) | Done | `backend/app/api/v1/tenants.py` |
| Plan limits + pricing + subscription-invoice generation | Done | `backend/app/services/tenant.py` |
| Login with tenant-slug disambiguation + 2FA | Done | `backend/app/services/auth.py` |
| Audit log (hash-chained), RBAC (default + custom roles), customer portal | Done | various |

## Gaps this plan addresses (found while reading the code)

1. **Tenant status is not enforced at runtime.** Login and the auth dependency only check
   `User.is_active`, never `tenant.status` (`auth.py:51`, `deps.py:37`). A **suspended or cancelled**
   tenant's users can still log in. Trial expiry is not enforced anywhere.
2. **Provisioning is incomplete.** `create_tenant` (`services/tenant.py:56`) only inserts a row — it does
   **not** create the first admin user, default RBAC roles, notification templates, or number sequences.
3. **Plan limits only half-wired.** `enforce_limit` is called for **users only** (`user.py:36`); sites and
   technicians have limits defined but no enforcement at creation.
4. **No tenant routing / white-label delivery.** `branding`/`settings` JSON exists but there's no
   subdomain/domain-based tenant resolution, and the frontend doesn't apply per-tenant logo/colors.
5. **No tenant offboarding.** No per-tenant data export or deletion (needed for cancellation / DPDP / GDPR).

## Scope & decisions (locked)

- **Go-to-market motion:** Sales-led. The platform admin (Durwankur) provisions each company. **No public signup.**
- **Billing:** **No payment gateway.** The existing `SubscriptionInvoice` model + plan pricing stay purely as
  internal record-keeping of what each company owes. Suspension on non-payment is **manual** via the existing
  `/suspend` endpoint. No online collection, no dunning, no auto-suspend.
- **Tenant routing:** Subdomain per tenant (`acme.cctvapp.com`), reusing the existing `slug` as the subdomain.

---

## Phase 1 — Tenant lifecycle enforcement (security-critical, do first)

A suspended/cancelled tenant can currently still log in — a live hole.

- Enforce `tenant.status` in `login()` and the shared auth dependency: block `SUSPENDED`/`CANCELLED`
  (and `TRIAL` past expiry) with a clear error.
- Add `trial_ends_at` to `Tenant`; daily Celery job auto-expires trials and flags them.
- Wire `enforce_limit` into **site** and **technician** creation (currently only users are enforced).
- Tests: cross-tenant isolation, suspended-login blocked, limit-exceeded blocked.

## Phase 2 — Provisioning automation (admin-driven)

Today `create_tenant` only inserts a row — no first admin, no defaults.

- **Provisioning service** called from the existing platform-admin `create_tenant` flow: seed default RBAC
  roles + permissions, notification templates, number sequences, default settings/branding, **and create the
  company's first admin user**.
- Return/send first-admin credentials (temp password + forced reset, or invite-email link) — no public signup involved.
- Platform-admin UI: "Add company" wizard (company details → plan → first admin) on top of the existing tenant console.

## Phase 3 — White-label & tenant resolution

Make each company experience "their" app.

- Subdomain → tenant resolution (`acme.cctvapp.com`) using the existing `slug`; feeds login + branding.
- Apply `branding` (logo, primary color, company name) in the React app via a tenant-config endpoint.
- **Tenant-admin self-service settings** (the company's own admin, not the platform admin): branding,
  business profile (GSTIN, address, invoice prefix), and their own users — within plan limits.

## Phase 4 — Isolation hardening & offboarding

Enterprise trust + clean cancellation.

- Audit that **every** tenant-scoped table has an RLS policy in migrations; add a test asserting RLS coverage;
  verify Celery tasks set tenant context.
- Per-tenant data **export** and **hard-delete** on cancellation (DPDP/GDPR), with a retention window.
- Per-tenant usage metering + tenant-tagged logs/metrics; backup/restore runbook.

---

## Sequencing

1. **Phase 1** — small, fixes a real security gap. Start here.
2. **Phase 2** — provisioning automation; medium.
3. **Phase 3** — white-label; medium.
4. **Phase 4** — hardening/offboarding; medium, partly parallel.
