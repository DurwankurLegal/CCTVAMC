# Test Run — Findings & Bug Report

**Date:** 2026-06-23
**Suites run:**
- Backend: `cd tests/backend && ../../backend/venv/bin/python -m pytest` → **312 passed**
- Frontend unit: `cd frontend && npm test` (Vitest) → **60 passed**
- Frontend E2E: Playwright specs present; require a live stack (not run in this pass).

Both automated suites are **green**. The defects below were **application-code
bugs/gaps** uncovered while building and running the tests.

> **Update — all four issues below are now FIXED** (2026-06-23). Each fix ships
> with a regression test asserting the corrected behaviour. Backend suite is
> **314 passed** (was 312 + 2 new regression tests). Details under each entry.

Legend — Severity: 🔴 High · 🟠 Medium · 🟡 Low · Status: ✅ Fixed

---

## 🟠 ✅ BUG-1 — Sales-order numbers come from an in-memory counter (not durable, not concurrency-safe)

**Where:** [backend/app/api/v1/sales_orders.py](../backend/app/api/v1/sales_orders.py)

```python
_SO_SEQ: dict[UUID, int] = {}

def _next_order_number(tenant_id: UUID) -> str:
    _SO_SEQ[tenant_id] = _SO_SEQ.get(tenant_id, 0) + 1
    return f"SO-{str(tenant_id)[:4].upper()}-{_SO_SEQ[tenant_id]:05d}"
```

**Problem:** The sequence lives in a module-level dict in the worker process.
- Resets to 0 on every restart/redeploy → number reuse and collisions.
- Not shared across Gunicorn/Uvicorn worker processes or pods → two workers
  issue `SO-...-00001` for the same tenant concurrently.
- Every other document number (invoices, POs, quotations, tickets) uses the
  DB-backed `app.services.sequences.next_number`; sales orders are the lone
  exception.

**Impact:** Duplicate / non-unique sales-order numbers in any multi-worker or
post-restart scenario. Financial/document-integrity risk.

**Fix:** Replace `_next_order_number` with
`await next_number(db, tenant_id, "sales_order", "SO")` (the same DB sequence
helper the other modules use).

**✅ Fixed:** `_next_order_number` / `_SO_SEQ` removed;
`create_order` now calls
`await next_number(db, current_user.tenant_id, "sales_order", "SO")` — the same
row-locked DB sequence the other modules use. Numbers are now
`SO-<year>-<00001>`, durable and concurrency-safe.
**Regression test:** `test_sales_order_numbers_are_unique_and_sequential`.

---

## 🟠 ✅ BUG-2 — SLA report date range silently drops same-day tickets (off-by-one upper bound)

**Where:** [backend/app/services/reports.py](../backend/app/services/reports.py) `ticket_sla_report` (and the breached-count query just below it)

```python
ServiceTicket.created_at >= from_date,
ServiceTicket.created_at <= to_date,
```

**Problem:** `created_at` is a `DateTime`, but `to_date` is a `date`. The
comparison coerces `to_date` to midnight (`to_date 00:00:00`), so a ticket
created at, say, `to_date 10:30` is **excluded** from the range. Querying
"from 1st to 31st" misses everything created after midnight on the 31st.

**Impact:** Under-counts tickets on the final day of any range → SLA
compliance %, totals, and breached counts are wrong for ranges ending "today".

**Fix:** Make the upper bound exclusive of the *next* day, e.g.
`created_at < to_date + timedelta(days=1)`, or cast both sides to `date`.

**✅ Fixed:** both range queries now use an exclusive upper bound of the next
day — `created_at < to_date + timedelta(days=1)` — so the entire `to_date` day
is included.
**Regression test:** `test_ticket_sla_counts_same_day_ticket` (raises a ticket
today, queries `from=to=today`, asserts `total_tickets >= 1`).

---

## 🟡 ✅ BUG-3 — `closed_at` is recorded but never returned by the API

**Where:**
- Model sets it: [backend/app/models/service_ticket.py:42](../backend/app/models/service_ticket.py) + [backend/app/services/service_ticket.py](../backend/app/services/service_ticket.py) (`obj.closed_at = datetime.now(...)`)
- Response omits it: [backend/app/schemas/service_ticket.py](../backend/app/schemas/service_ticket.py) (`ServiceTicketResponse` exposes `resolved_at` but not `closed_at`)

**Problem:** Closing a ticket persists `closed_at`, but `ServiceTicketResponse`
has no `closed_at` field, so API/UI clients can never read when a ticket was
closed (only that `status == "closed"`).

**Impact:** Closure timestamp is invisible to the frontend and portal —
incomplete audit/SLA reporting surface.

**Fix:** Add `closed_at: Optional[datetime]` to `ServiceTicketResponse`.

**✅ Fixed:** added `closed_at: Optional[datetime]` to `ServiceTicketResponse`.
**Regression test:** `test_close_ticket_sets_closed_at` now asserts both
`status == "closed"` and `closed_at is not None`.

---

## 🟡 ✅ OBS-4 — Missing-credential responses are `403`, not `401`

**Where:** [backend/app/core/deps.py](../backend/app/core/deps.py) — `bearer_scheme = HTTPBearer()`

**Problem:** FastAPI's default `HTTPBearer` raises **403 Forbidden** when the
`Authorization` header is absent. The correct REST semantics for "no
credentials supplied" is **401 Unauthorized** (with a `WWW-Authenticate`
header). Invalid/expired tokens already return 401 correctly; only the
*missing-header* case is off.

**Impact:** Low — cosmetic/standards correctness; some clients branch on 401 to
trigger a re-login.

**✅ Fixed:** `bearer_scheme = HTTPBearer(auto_error=False)` plus a shared
`_require_credentials()` helper that raises **401** with
`WWW-Authenticate: Bearer` when the header is absent — applied to both
`get_current_user` and `get_current_portal_user`.
**Regression test:** `test_auth_me_no_token_returns_401` now asserts exactly
`401` and the `WWW-Authenticate: Bearer` header. (Per-resource guard tests keep
the tolerant `in (401, 403)` assertion, which still holds.)

---

## ℹ️ NOTE-5 — Environment caveat: SQLite drops timezone info (not an app bug)

Integration tests run on in-memory SQLite. Columns declared
`DateTime(timezone=True)` round-trip as **naive** datetimes there, so
`sla_due_at` deserializes without an offset. PostgreSQL preserves the offset, so
this is a test-environment artifact, not a production defect. The SLA tests
normalise naive/aware datetimes before comparing. PostgreSQL Row-Level Security
is likewise not exercised under SQLite — run with
`TEST_DATABASE_URL=postgresql+asyncpg://…` to cover RLS.

---

## Summary

| ID | Severity | Status | Area | One-line |
|----|----------|--------|------|----------|
| BUG-1 | 🟠 Medium | ✅ Fixed | sales_orders | SO numbers from in-memory counter → now DB sequence |
| BUG-2 | 🟠 Medium | ✅ Fixed | reports | SLA date range excluded same-day tickets → exclusive next-day upper bound |
| BUG-3 | 🟡 Low | ✅ Fixed | service_tickets | `closed_at` now exposed in API response |
| OBS-4 | 🟡 Low | ✅ Fixed | auth | Missing-token now returns 401 + WWW-Authenticate |
| NOTE-5 | ℹ️ | n/a | test env | SQLite tz/RLS caveat (not an app bug) |

All four are fixed with regression coverage; both test suites are green
(backend **314 passed**, frontend **60 passed**).

### Files changed by the fixes
- `backend/app/api/v1/sales_orders.py` (BUG-1)
- `backend/app/services/reports.py` (BUG-2)
- `backend/app/schemas/service_ticket.py` (BUG-3)
- `backend/app/core/deps.py` (OBS-4)
- Tests: `test_sales_orders.py`, `test_reports.py`, `test_service_tickets.py`, `test_auth_flow.py`
