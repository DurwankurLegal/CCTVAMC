# QA Assessment Report — End-to-End Browser Testing

**Application:** CCTV AMC & Service Management Platform (multi-tenant SaaS)
**Test type:** Functional · Integration · Usability · Data-validation · Security (black-box, real-browser)
**Method:** Driven through the actual browser UI (Vite frontend → FastAPI backend → PostgreSQL/Redis), exactly as an end user.
**Date:** 2026-06-23
**Build under test:** branch `feat/phase1-gap-remediation`

---

> ## ✅ Update — all findings fixed & re-verified in the browser (2026-06-23)
> | ID | Fix | Browser re-test |
> |----|-----|-----------------|
> | BUG-01 | `client.ts` interceptor: skip auth endpoints + one-shot `_retry` guard; surface error. authSlice shows backend detail. | Wrong password → **1** `POST /auth/login` (was 462), button recovers, shows **"Invalid credentials"** |
> | BUG-02 | `RequirePerm` route guard in `App.tsx` (+ `hasPerm` in `menu.ts`) on all restricted routes | Technician → `/users` now **redirects to `/dashboard`** |
> | BUG-03 | Optional "Company code" (tenant_slug) field added to staff login | Field renders; forwarded to `/auth/login` when set |
> | BUG-04 | Ant `type:'email'` rule + `apiErrorMessage()` maps backend 422 to a readable toast | Bad email → inline **"Enter a valid email address"**, no server round-trip |
> | BUG-05 | Seed AMC numbers aligned to the generator's 4-digit format (`AMC-2026-0001`) | Format consistent on fresh seed |
>
> Frontend unit tests: **60 passed** after the changes. Files touched:
> `frontend/src/api/client.ts`, `frontend/src/store/authSlice.ts`,
> `frontend/src/store/customerSlice.ts`, `frontend/src/pages/LoginPage.tsx`,
> `frontend/src/pages/CustomersPage.tsx`, `frontend/src/utils/menu.ts`,
> `frontend/src/App.tsx`, `backend/scripts/seed.py`, + 2 unit-test mocks.
> (OBS-1…4 remain as low-priority polish.)

## 1. Executive summary

The full stack was launched (Postgres + Redis via Docker, Alembic migrations, seeded data, uvicorn backend on :8000, Vite frontend on :5173) and exercised through the browser across **all 20 staff modules + the customer portal**.

**Overall:** The application is broadly functional. Core CRUD, multi-step workflows (service-ticket raise, lead→customer conversion), dashboards, role-based menu filtering, and the customer portal all work and **persist data correctly** end-to-end (frontend → API → DB verified).

However, testing uncovered **1 Critical, 1 High, 2 Medium, and 1 Low defect**, plus several usability observations. The Critical issue (an infinite login/refresh request storm on failed login) should block release.

| Severity | Count |
|----------|-------|
| 🔴 Critical | 1 |
| 🟠 High | 1 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |
| ℹ️ Observations | 4 |

---

## 2. Environment & setup

| Component | Detail |
|-----------|--------|
| Infra | `docker compose -f infra/docker-compose.dev.yml` (postgres:16, redis:7) |
| DB state | Alembic at head `012`; seeded via `python -m scripts.seed` |
| Backend | uvicorn `app.main:app` :8000 — `GET /health` → `{"status":"ok"}` |
| Frontend | Vite dev server :5173 (proxies `/api` → :8000) |
| Seed logins | admin@durwankur.ai / Admin@1234 (tenant admin); tech@durwankur.ai / Passw0rd@123 (technician); portal@greenvalley.in / Passw0rd@123 (portal, slug `durwankur`) |

---

## 3. Coverage & results

| Area | Scenario | Result |
|------|----------|--------|
| Auth | Invalid credentials | 🔴 **FAIL — BUG-01** (infinite loop, no error shown) |
| Auth | Valid login → dashboard | ✅ Pass |
| Auth | Logout → redirect to /login, token cleared | ✅ Pass |
| Auth | Empty-form validation | ✅ Pass (required + email format on login form) |
| Dashboard | KPI cards + AMC/Invoice tables render with live data | ✅ Pass |
| Customers | List render | ✅ Pass |
| Customers | Create — required-field validation | ✅ Pass |
| Customers | Create — invalid email | 🟡 **Partial — BUG-04** (no client validation; backend 422 not clearly surfaced) |
| Customers | Create — valid (persisted, shown in table) | ✅ Pass |
| Service Tickets | Raise ticket (customer+priority+complaint), SLA set, persisted | ✅ Pass (TKT-2026-00002, high, SLA OK) |
| Leads | Convert lead → customer (business workflow, persisted) | ✅ Pass (City Hospital created) |
| All modules | Quotations, AMC, Engineer Visits, Installations, Assets, Vendors, Inventory, Invoices, Payments, Reports, Notifications, Users — load without crashes | ✅ Pass |
| RBAC | Technician menu is role-filtered (6 of 16 items) | ✅ Pass |
| RBAC | Technician opens admin `/users` by direct URL | 🟠 **FAIL — BUG-02** (page renders; data blocked by backend 403) |
| Multi-tenant login | Email-in-two-tenants disambiguation from UI | 🟡 **FAIL — BUG-03** (no tenant field on staff login) |
| Portal | Login with tenant_slug → scoped dashboard | ✅ Pass |
| Data integrity | Created/converted records persisted to DB and re-read via API | ✅ Pass (9 customers confirmed) |

---

## 4. Bug reports

### 🔴 BUG-01 — Failed login triggers an infinite login↔refresh request storm (Critical / Blocker)

**Module:** Authentication — `frontend/src/api/client.ts` (axios response interceptor)

**Steps to reproduce:**
1. Be logged in once (so a valid `refresh_token` is in `localStorage`), then log out is **not** required — any stale refresh token triggers it. Navigate to `/login`.
2. Enter a valid email with a **wrong password**; click **Sign In**.

**Expected:** One `POST /auth/login` → 401; an "Invalid credentials" error message; button returns to idle.

**Actual:** The login button is stuck on **loading indefinitely**, no error is shown, and the app fires an **unbounded loop of `POST /auth/login` (401) → `POST /auth/refresh` (200) → retry login (401) → …**. A single click generated **462 requests** (measured in backend log) before I force-cleared `localStorage` to stop it.

**Root cause:** The global response interceptor applies token-refresh-and-retry logic to **every** 401 — including the `/auth/login` request itself — and has **no `_retry` guard**. When a stale refresh token exists, `/auth/refresh` keeps succeeding and the failed login is retried forever.

```js
// client.ts
if (error.response?.status === 401) {
  const refreshToken = localStorage.getItem("refresh_token");
  if (refreshToken) {
    const { data } = await axios.post("/api/v1/auth/refresh", ...);
    ...
    return apiClient.request(error.config);   // ← retries /auth/login forever
  }
}
```

**Impact:** Client-side hang + a request flood that hammers the backend (effectively a self-inflicted DoS) on a routine wrong-password attempt. User never sees why login failed.

**Recommended fix:** (a) Skip the refresh/retry branch for auth endpoints (`/auth/login`, `/auth/refresh`); (b) add a one-shot `config._retry` guard so a request is retried at most once; (c) surface the original error so the login error message renders.

---

### 🟠 BUG-02 — Missing frontend route-level RBAC guards (High — defense-in-depth)

**Module:** Routing / authorization (`frontend/src/App.tsx` route definitions)

**Steps to reproduce:**
1. Log in as **technician** (tech@durwankur.ai). The sidebar correctly shows only 6 permitted modules.
2. Manually navigate to `http://localhost:5173/users`.

**Expected:** Redirect to dashboard / "not authorized" — restricted screens should not be reachable by non-permitted roles.

**Actual:** The **"Users & Roles" admin page renders**, including the **"Add User"** button and the table layout. The data table shows *No data* because the backend correctly returns **403** on `GET /users` and `GET /users/roles` (verified in network log) — so **no data leaks** — but the admin-only UI is exposed and the user can attempt actions that will fail confusingly.

**Impact:** Improper UI exposure of privileged screens to lower-privilege roles. No data breach (API enforces RBAC), but it's a defense-in-depth and UX correctness gap. The same applies to other hidden routes (`/invoices`, `/payments`, `/vendors`, `/reports`, etc.).

**Recommended fix:** Wrap routes in a permission-aware guard (reuse the same permission set that drives `filterTenantMenu`) that redirects unauthorized roles, instead of relying only on hiding menu items.

---

### 🟡 BUG-03 — Staff login cannot disambiguate emails that exist in multiple tenants (Medium)

**Module:** Login UI (`frontend/src/pages/LoginPage.tsx`) vs auth service (`backend/app/services/auth.py`)

**Detail:** The staff login form has **only email + password — no tenant/service-provider field**. The backend resolves tenant by email when no slug is given, but if the **same email exists in two tenants** it returns `400 "Email exists in multiple tenants; specify tenant_slug"`. Because the form provides no way to supply `tenant_slug`, **such a user can never log in through the UI**.

**Expected:** Either emails are globally unique, or the login form lets the user pick/enter their tenant (the customer portal login already has this field).

**Actual:** Multi-tenant-email users are locked out of the staff app.

**Impact:** Login lockout for a legitimate (and architecturally supported) account configuration. Medium because it depends on email reuse across tenants, which the backend explicitly anticipates.

**Recommended fix:** Add an optional "Service provider code" (tenant_slug) field to the staff login form (mirroring the portal login), and forward it to `/auth/login`.

---

### 🟡 BUG-04 — Customer form: no client-side email validation; backend 422 not clearly surfaced (Medium/Low)

**Module:** Customers create/edit (`frontend/src/pages/CustomersPage.tsx`)

**Steps to reproduce:**
1. Customers → Add Customer. Name = "QA Test", Category = Commercial, Email = `not-an-email`. Click Create.

**Expected:** Inline "Enter a valid email" before submit, or a clear actionable error.

**Actual:** No client-side email validation (the field is `<Input type="email">` with no Ant rule). The request hits the backend which correctly rejects it with **422**, but the only user feedback is a generic transient toast (`Save failed` / "Request failed with status code 422") — not field-level or actionable. The modal stays open with no inline error. (Valid data creates and persists correctly.)

**Impact:** Poor validation UX; users get an unhelpful error and may not realise the email is the problem.

**Recommended fix:** Add an Ant `rules={[{ type: 'email' }]}` to the email field, and map backend 422 `detail` into field-level errors / a readable message.

---

### 🟢 BUG-05 — Inconsistent document-number formats for AMC contracts (Low)

**Module:** AMC numbering (seed vs `next_number` generator)

**Detail:** AMC contract numbers in the same tenant use **three different formats**: `AMC-2026-002` / `AMC-2026-001` (3-digit, seed), `AMC-2026-005` and `AMC-2026-0001` / `AMC-2026-0002` (4-digit). Mixed zero-padding widths and counters look unprofessional on customer-facing documents and complicate sorting/search. (Same class as the sales-order numbering issue fixed earlier in `tests/BUGS.md` BUG-1.)

**Recommended fix:** Standardise all document numbering on the DB `next_number` sequence with a single fixed width; backfill/normalise legacy/seed numbers.

---

## 5. Usability & technical observations (Low / non-blocking)

- **OBS-1 — Irreversible action without confirmation:** Leads → **Convert** converts a lead to a customer on a single click with no confirmation dialog. Recommend a confirm step.
- **OBS-2 — Leads list "Category" column shows "—"** for all rows (leads have no category populated/displayed). Cosmetic/data-display.
- **OBS-3 — Deprecated Ant Design API:** console is full of `[antd: Dropdown] dropdownRender is deprecated, use popupRender`. Tech-debt; will break on Ant Design v6.
- **OBS-4 — Seed data quirk:** portal user `portal@greenvalley.in` is linked to the **"Sunrise Apartments"** customer (name/email mismatch). Confirm intended linkage in seed data.

---

## 6. What works well (positive findings)

- End-to-end **data persistence is solid** — every created/converted record was re-read from the DB via API (customers 7→9 across a create + a conversion).
- **Backend authorization is correctly enforced** (RBAC 403s, no data leakage to the technician role) — the API is the real security boundary and it holds.
- **Multi-step business workflows work**: service-ticket raise sets the SLA by priority; lead→customer conversion creates the customer and flips lead status.
- **All 20 staff modules + portal render without runtime/JS crashes**; empty modules (Assets, Vendors, Inventory, Engineer Visits) are genuinely empty in seed data (confirmed via API), and show correct empty states.
- **Customer portal** correctly requires a tenant code and shows tenant/customer-scoped data only.

---

## 7. Recommendations (priority order)

1. **Fix BUG-01 before release** — it is a guaranteed hang + request flood on the most common error path (wrong password).
2. Add **frontend route guards** (BUG-02) to match the backend's RBAC.
3. Add a **tenant field to staff login** (BUG-03).
4. Add **client-side email validation + readable 422 mapping** (BUG-04), and standardise document numbering (BUG-05).
5. Address the Ant Design deprecation (OBS-3) before upgrading the UI library.

> Note: the backend-only defects found earlier (sales-order numbering, SLA date range, `closed_at` exposure, 401-vs-403) are tracked and **already fixed** in `tests/BUGS.md`. This report covers the browser/E2E layer.
