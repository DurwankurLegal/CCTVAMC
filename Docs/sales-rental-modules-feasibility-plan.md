# Feasibility Assessment & Implementation Plan
## Computer Hardware & CCTV — Sales Module and Rental Module

**Document type:** Feasibility study + phased implementation plan (no code in this document)
**Prepared for:** Durwankur Technologies Pvt. Ltd. — CCTV AMC & Service Management SaaS
**Date:** 2026-06-25
**Status:** Draft for review — *implementation NOT started*

---

## 1. Executive Summary

The platform is a mature, multi-tenant FastAPI + React SaaS already running the
full service lifecycle (leads → customers → quotations → AMC → tickets →
visits → invoicing → payments) with strong cross-cutting infrastructure:
tenant isolation (app layer + PostgreSQL RLS), audit hash-chaining, GST
computation, document numbering, a central notification engine, and RBAC.

**Verdict: Both modules are feasible and architecturally low-risk.** They map
naturally onto patterns the codebase already uses, and a large share of the
needed plumbing already exists.

| Module | Feasibility | Reuse of existing code | Net-new build | Est. effort |
|---|---|---|---|---|
| **1. Hardware & CCTV Sales** | High — mostly *completing* partial work | ~60% | Product catalog, stock-linked fulfilment, SO→Invoice automation, returns, full UI | **Medium** (~3–4 weeks) |
| **2. Hardware & CCTV Rental** | High — but largely *net-new domain* | ~35% | Rental units, rate plans, bookings/availability, check-out/in, recurring rental billing, deposits | **Medium-High** (~5–6 weeks) |

The single most important finding: **a Sales backend already exists but is
incomplete and has no UI**, and **there is no Product catalog or Rental domain
at all**. Sales is therefore a "finish + harden" effort; Rental is a "new
module following established patterns" effort.

---

## 2. Current-State Analysis (what already exists)

### 2.1 Architectural building blocks we will reuse

| Capability | Where it lives | Relevance |
|---|---|---|
| Tenant isolation base repo (app filter + RLS + audit on every write) | `backend/app/repositories/base.py` (`TenantRepository`) | Every new table/model uses this — isolation & audit come "for free" |
| Generic CRUD factory | `backend/app/services/crud_base.py` (`make_crud`) | New simple services need almost no boilerplate |
| Tenant model mixin (uuid id, tenant_id, timestamps) | `backend/app/models/base.py` (`TenantMixin`) | Standard base for all new models |
| Gapless per-tenant document numbering | `backend/app/services/sequences.py` (`next_number`) | Sales orders, rental contracts, invoices get clean numbers |
| GST computation (CGST/SGST/IGST, intra/inter-state, Decimal-safe) | `backend/app/services/gst.py` (`compute_gst_totals`) | Reused verbatim for sales invoices and rental invoices |
| RBAC permission catalogue + role matrix | `backend/app/core/permissions.py` | Add new `<module>:read/write` entries |
| Central notification engine (templated, multi-channel) | `backend/app/services/notification.py`, `notification_events.py` | Rental due/overdue/return-reminder, low-stock, order-confirmed |
| RLS migration pattern | `backend/migrations/versions/*` (`ENABLE/FORCE ROW LEVEL SECURITY` + `tenant_isolation` policy) | Copy pattern for new tables |
| Tenant offboarding ordered deletes | `backend/app/services/offboarding.py` (`ORDERED_DELETES`) | New tables must be appended here (child-first) |
| Frontend page + RBAC routing + menu pattern | `frontend/src/App.tsx` (`tenantMenu`, `RequirePerm`), `frontend/src/api/client.ts`, `frontend/src/utils/menu.ts` | New pages plug in with one menu entry + one guarded route each |

### 2.2 Domain pieces that already exist (directly relevant)

- **Inventory** — `inventory_items` (part number, HSN, GST rate, stock, van stock,
  unit cost, reorder level) + `inventory_movements` (purchase/sale/consumption/
  transfer/adjustment/return, with `reference_type`/`reference_id` back-pointers)
  and a working `adjust_stock` service with low-stock alerts.
  → This is our **stock ledger** for sales fulfilment.
- **Sales Orders** — `sales_orders` model (order_number, customer, optional
  quotation link, status draft/confirmed/fulfilled/cancelled, JSON line items,
  subtotal/total) + a **minimal API** (`backend/app/api/v1/sales_orders.py`).
  ⚠️ **Incomplete:** no GST fields, no stock decrement on fulfilment, no
  invoice generation, no delivery/serial capture, **no frontend page**.
- **Quotations** — full model with GST + status workflow; `quotation_id` already
  referenced by sales orders. The quote → order chain is half-wired.
- **Invoices** — full GST tax-invoice model with `sales_order_id` field already
  present, credit-note support, PDF url, partial-payment tracking.
- **Payments** — exists and links to invoices.
- **CCTV Assets** — `cctv_assets` (serial, make, model, type, warranty, status:
  active/faulty/under_repair/replaced/decommissioned) tied to **customer sites**.
  → Useful precedent for **serialized unit tracking**; the Rental module needs a
  similar but tenant-owned, customer-independent "rental unit" concept.
- **AMC Contracts** — recurring, date-bounded, billable agreements.
  → Closest existing precedent for **rental contracts & recurring rental billing**.

### 2.3 Gaps (what does NOT exist today)

1. **No Product / SKU catalog** distinct from inventory consumables. Sales needs
   sellable products (cameras, DVRs, NVRs, switches, HDDs, accessories) with
   pricing, brand/model, warranty terms, serial-tracked flag.
2. **No serial-number capture at point of sale** (which physical units shipped).
3. **No Sales Order → Invoice automation** and no stock movement on fulfilment.
4. **No Sales UI** at all.
5. **No Rental domain** whatsoever — no rentable assets, rate plans, bookings,
   availability, check-out/check-in, rental billing, deposits, or damage/late fees.
6. **No depreciation / asset-ownership ledger** for tenant-owned rental hardware.

---

## 3. Module 1 — Computer Hardware & CCTV Sales

### 3.1 Functional scope

End-to-end outright sale of hardware:

- **Product catalog** (sellable SKUs; serial-tracked vs non-serial).
- **Sales quotation → sales order → delivery/fulfilment → tax invoice → payment.**
- **Stock-linked fulfilment**: confirming/fulfilling an order decrements
  inventory and records `sale` movements; cancellation/return reverses them.
- **Serial capture** at dispatch; optionally auto-register sold CCTV units as
  customer-site assets (links Sales → existing Asset/AMC modules).
- **Returns / RMA & credit notes** (reuses invoice credit-note support).
- **Reporting**: sales by period/product/customer, margin (sell vs `unit_cost`),
  pending fulfilment, stock-out risk.

### 3.2 Feasibility — HIGH

Most of the chain exists; this is primarily *completing and connecting*
existing pieces plus adding a catalog and a UI. No architectural changes needed.

### 3.3 Data model changes

| Table | Action | Notes |
|---|---|---|
| `products` | **NEW** | SKU, name, brand, model, category (camera/DVR/NVR/switch/HDD/accessory), HSN, default GST rate, sale price, `is_serial_tracked`, warranty months, `inventory_item_id` link (stock source), `is_active` |
| `sales_orders` | **EXTEND** | Add GST columns (cgst/sgst/igst, supply_state_code) to mirror invoices; add `fulfilled_at`, `invoice_id` back-link; richer line-item shape (product_id, qty, unit_price, gst_rate, serials[]) |
| `sales_order_items` (optional) | **NEW (optional)** | Promote JSON line items to a child table if per-line serial tracking / partial fulfilment is required. Default: keep JSON for parity with quotations/invoices unless partial fulfilment is in scope |
| `inventory_movements` | **REUSE** | Already supports `sale`/`return` with reference back-pointers |
| `invoices` | **REUSE** | `sales_order_id` field already exists |

> **Design decision to confirm:** keep line items as JSON (consistent with
> quotations/invoices, fastest) **vs.** a normalized `sales_order_items` table
> (needed only if you want partial fulfilment, per-line serials as first-class
> rows, and line-level reporting). Recommendation: start JSON, add child table
> only if partial fulfilment becomes a requirement.

### 3.4 Backend work

- `products` model + schema + service (via `make_crud`) + `/api/v1/products` router.
- Extend `sales_order` service: GST via `compute_gst_totals`; on
  `confirm`/`fulfil`, decrement stock through `inventory.adjust_stock` (movement
  type `sale`, `reference_type="sales_order"`); on cancel/return, reverse.
- `POST /sales-orders/{id}/fulfil` and `POST /sales-orders/{id}/invoice`
  (generate tax invoice from the order).
- Optional: auto-create `cctv_assets` rows for serial-tracked CCTV items shipped
  to a customer site.
- Notifications: order confirmed, ready-for-dispatch, low-stock (already wired).
- Migration: create `products`, alter `sales_orders`, add RLS policies, append
  new tables to `offboarding.ORDERED_DELETES`.
- Permissions: add `products` (and confirm `sales_orders`) to `MODULES`.

### 3.5 Frontend work

- `ProductsPage.tsx` (catalog CRUD).
- `SalesOrdersPage.tsx` (**new** — none exists): list/create/confirm/fulfil,
  line-item editor with product picker, serial entry on dispatch, "Generate
  Invoice" action.
- Wire routes + `tenantMenu` entries + `RequirePerm` guards in `App.tsx`.
- Reuse existing Invoices/Payments pages for the downstream steps.

### 3.6 Sales effort estimate

~3–4 weeks (1 backend + 1 frontend dev): catalog (3d), SO completion + stock +
invoice automation (5d), serial/asset linkage (2d), returns/credit notes (2d),
UI (5–6d), tests (3d).

---

## 4. Module 2 — Computer Hardware & CCTV Rental

### 4.1 Functional scope

Lease tenant-owned hardware to customers for a period:

- **Rental catalog & units**: rentable products and individually trackable,
  serialized **rental units** (owned by the tenant, with condition/availability
  status), distinct from goods sold.
- **Rate plans**: daily / weekly / monthly / custom; security deposit; min
  rental period.
- **Rental booking/order**: reserve units for a date range → contract.
- **Availability**: prevent double-booking a unit across overlapping date ranges.
- **Check-out / Check-in**: dispatch with condition + meter/notes; return with
  condition assessment, late fee, damage charges.
- **Recurring rental billing**: periodic invoices for the rental term
  (monthly/weekly), proration, deposit handling, final settlement.
- **Lifecycle**: maintenance hold, retirement; optional depreciation ledger.

### 4.2 Feasibility — HIGH (but mostly net-new)

No rental domain exists, but every needed pattern does:
- **Recurring, date-bounded, billable contract** → mirror **AMC**.
- **Serialized unit with status** → mirror **CCTV Asset**.
- **Invoice + GST + payments** → reuse as-is.
- **Notifications** (due, overdue, return reminder) → reuse engine.

The only genuinely new algorithmic piece is **availability / overlap checking**
to prevent double-booking — a well-understood date-range query, low risk.

### 4.3 Data model changes (all NEW)

| Table | Purpose |
|---|---|
| `rental_products` | Rentable catalog item (or reuse `products` with a `rentable` flag + rental attributes) |
| `rental_units` | Serialized physical unit owned by tenant: serial, make/model, purchase cost & date, condition, status (available/reserved/on_rent/maintenance/retired) |
| `rental_rate_plans` | Per product/unit: daily/weekly/monthly rate, deposit, min period |
| `rental_contracts` | Customer, site, start/end dates, status (booked/active/returned/closed/cancelled), deposit, billing cycle — AMC-shaped |
| `rental_contract_lines` | Units/products on the contract, qty, rate, period |
| `rental_movements` (or reuse pattern) | check-out / check-in events with condition + charges |
| `invoices` | **REUSE** — add `rental_contract_id` (nullable), like `amc_contract_id` |

> **Design decision to confirm:** one unified `products` table with
> `is_sellable` / `is_rentable` flags **vs.** separate `rental_products`.
> Recommendation: **one catalog** (`products`) with flags — avoids duplication,
> a single SKU can be both sold and rented.

### 4.4 Backend work

- Models/schemas/services for units, rate plans, contracts, lines, movements.
- **Availability service**: given product/unit + date range, return free units
  (overlap query excluding cancelled/returned). Guard booking against conflicts.
- **Check-out / check-in** endpoints: flip unit status, record condition,
  compute late/damage fees.
- **Recurring billing**: a Celery job (workers already exist) generates periodic
  rental invoices per active contract per cycle; proration on partial periods;
  GST via `compute_gst_totals`.
- **Deposit & settlement**: capture deposit (payment), refund/adjust on closure.
- Notifications: booking confirmed, rental starting/ending, overdue return,
  payment due (reuse engine + new templates).
- Migration: new tables + RLS policies + alter `invoices`; append to
  `offboarding.ORDERED_DELETES` (child-first: lines/movements → contracts →
  units → rate plans → products).
- Permissions: add `rentals` (or split `rental_contracts` / `rental_units`) to
  `MODULES`.

### 4.5 Frontend work

- `RentalUnitsPage.tsx` (fleet inventory + status).
- `RentalContractsPage.tsx` (booking with availability check, check-out/check-in,
  view billing schedule).
- Rate-plan management (small page or section).
- Routes + menu + `RequirePerm`; reuse Invoices/Payments for billing/deposits.

### 4.6 Rental effort estimate

~5–6 weeks: data model + migrations (4d), units/rate plans/contracts CRUD (5d),
availability engine (3d), check-out/in + fees (4d), recurring billing job +
deposits (5d), notifications (2d), UI (7–8d), tests (4d).

---

## 5. Cross-cutting requirements (apply to BOTH modules)

Every new module **must** comply with established platform invariants:

1. **Tenant isolation** — all models use `TenantMixin`; all access goes through a
   `TenantRepository` subclass (never raw queries bypassing tenant filter).
2. **RLS** — each new table gets `ENABLE/FORCE ROW LEVEL SECURITY` + the
   `tenant_isolation` policy in its migration.
3. **Audit** — writes through `TenantRepository` auto-append to the hash-chained
   audit log; do not bypass it.
4. **Document numbering** — use `next_number` for SO / rental contract / invoice
   numbers (new `doc_type`s, e.g. `RENTAL`, prefix `RNT`).
5. **GST** — use the shared `compute_gst_totals`; never re-implement tax math.
6. **Notifications** — route all messaging through `NotificationService.send()`
   with DB templates; add new events to `notification_events.py`.
7. **RBAC** — add new modules to `MODULES` and the `DEFAULT_ROLE_MATRIX`; guard
   write endpoints with `require_permission(...)` and frontend routes with
   `RequirePerm`.
8. **Offboarding** — append new tables to `ORDERED_DELETES` in child-first order,
   or tenant hard-delete will FK-fail.
9. **Tests** — add backend pytest coverage (router + service) and frontend vitest;
   the suite currently runs 312 backend + 60 frontend tests (see `tests/`).
10. **Migrations** — Alembic revision per module, with working `downgrade()`.

---

## 6. Recommended phasing

| Phase | Scope | Rationale |
|---|---|---|
| **Phase A** | Product catalog (`products`) | Shared foundation for both modules; smallest, lowest-risk first |
| **Phase B** | Complete **Sales** (stock-linked SO, invoice automation, serials, UI, returns) | Highest reuse, fastest visible value; de-risks the catalog |
| **Phase C** | **Rental** core (units, rate plans, contracts, availability, check-out/in, UI) | Net-new domain, builds on Phase A catalog |
| **Phase D** | **Rental** billing (recurring invoice job, deposits, settlement, late/damage fees) | Most complex; depends on Phase C being stable |
| **Phase E** | Reporting & dashboards for both; optional asset/AMC auto-linkage | Polish & analytics |

---

## 7. Risks & open decisions

| # | Item | Recommendation |
|---|---|---|
| R1 | JSON line items vs normalized child tables | Start JSON (parity with quotations/invoices); normalize only if partial fulfilment / line-level serials required |
| R2 | Unified `products` catalog vs separate sales/rental catalogs | **Unified** with `is_sellable`/`is_rentable` flags |
| R3 | Double-booking prevention | Date-range overlap query + DB-level guard; add unit-status check at check-out |
| R4 | Recurring rental billing engine | Reuse Celery workers + AMC billing precedent; idempotent per (contract, period) |
| R5 | Depreciation / asset ownership ledger | Out of scope for MVP; flag as future phase unless finance requires it now |
| R6 | Serial-tracked sold units → auto-create `cctv_assets` | Make optional/configurable per tenant |
| R7 | RLS regression | Add an RLS isolation test per new table (pattern exists in suite) |

### Decisions needed from product owner before build
1. Is **partial fulfilment** of a sales order in scope? (drives R1)
2. Is **rental depreciation/finance ledger** required for MVP? (drives R5)
3. Rental billing granularity: monthly only, or daily/weekly too?
4. Should sold CCTV units **auto-register as customer assets** (enabling AMC upsell)?

---

## 8. Conclusion

Both modules are **feasible with no architectural changes** and should be built
strictly on the platform's existing patterns (TenantRepository, RLS migrations,
shared GST/numbering/notification services, RBAC, offboarding deletes).

- **Sales** is a *completion* effort — the backend skeleton, inventory ledger,
  quotation/invoice/payment chain, and GST all exist; the work is connecting
  them, adding a product catalog, and building the missing UI. **~3–4 weeks.**
- **Rental** is a *new module* but every required pattern has a direct in-repo
  precedent (AMC for recurring contracts, CCTV Asset for serialized units,
  invoices/payments/notifications for billing). The only novel logic is
  availability/overlap checking. **~5–6 weeks.**

Recommended order: **Catalog → Sales → Rental core → Rental billing → Reporting.**
