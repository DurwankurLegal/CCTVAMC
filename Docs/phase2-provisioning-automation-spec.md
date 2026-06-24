# Phase 2 — Provisioning Automation: File-Level Implementation Spec

> Status: Spec only — not yet implemented.
> Parent plan: `Docs/phase2-multitenant-saas-plan.md`
> Prereq: Phase 1 (`Docs/phase1-lifecycle-enforcement-spec.md`) — implemented.
> Date: 2026-06-24

## Goal

Make onboarding a company a single action. Today `create_tenant`
(`services/tenant.py:56`) only inserts a tenants row — no first admin, no
workspace defaults. After this phase, the platform admin's "Onboard Tenant"
flow creates a ready-to-use workspace: **first admin user**, default
settings/branding, and seeded notification templates — returning the first
admin's one-time credentials.

## What the codebase already gives us (so we DON'T re-build it)

Verified while scoping — these correct the parent plan's bullet list:

- **Document number sequences are lazy.** `services/sequences.py:next_number` creates
  the `DocumentSequence` row on first use. **No seeding required.**
- **The global permission catalogue is already seeded** in migration `002`
  (`INSERT INTO permissions ...`), and `core/permissions.py:DEFAULT_ROLE_MATRIX`
  resolves effective permissions from the legacy `User.role` string **without any
  per-tenant rows**. So a new tenant's users work immediately. Seeding per-tenant
  DB `Role` rows is **optional** — only needed if tenant admins will customise roles
  in-app (deferred; see Out of scope).
- **Notification templates fall back gracefully.** `services/notification.py` emits a
  generic message when no `NotificationTemplate` row exists, so events are never
  dropped. Seeding per-tenant templates is therefore **recommended (branding /
  editability), not required for function.**

Net: the *required* new work is the **first admin user + credential handling**;
template seeding is a recommended add-on; role seeding is out of scope.

## Decisions (locked)

- **Credential model:** generate a **temporary password**, returned **once** in the
  provisioning API response for the platform admin to convey, and force a reset at
  first login via a new `User.must_change_password` flag. (No invite-token table —
  simpler; the email path is an optional enhancement noted at the end.)
- **Back-compat:** first-admin fields are **optional** on the create request. When
  absent, `POST /tenants` behaves exactly as today (keeps existing tenant tests
  green); when present, it provisions the admin and returns credentials.
- **Idempotent seeding:** template seeding skips event/channel pairs that already
  exist for the tenant, so re-running provisioning is safe.

---

## Step 1 — `User.must_change_password` flag

### 1a. `backend/app/models/user.py`
Add to `User`:
```python
must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### 1b. New migration `backend/migrations/versions/014_user_must_change_password.py`
`down_revision = "013"`. Mirror the `009`/`013` style:
```python
def upgrade() -> None:
    op.add_column("users", sa.Column(
        "must_change_password", sa.Boolean(), nullable=False, server_default="false"))

def downgrade() -> None:
    op.drop_column("users", "must_change_password")
```

---

## Step 2 — Default notification-template catalogue

### `backend/app/services/notification_templates.py` (new)
Code-defined defaults seeded per tenant. Enumerate the event constants in
`services/notification_events.py` (e.g. `AMC_EXPIRY`, `SLA_BREACH`, `PAYMENT_DUE`, …)
— one entry per (event_type, channel) you want branded:
```python
from app.models.notification import NotificationChannel
from app.services import notification_events as ev

# (event_type, channel, subject, body) — {{var}} placeholders match the context
# dicts each call site already passes to NotificationService.send().
DEFAULT_TEMPLATES = [
    (ev.AMC_EXPIRY,  NotificationChannel.EMAIL,
     "AMC {{contract_number}} expiring in {{days}} days",
     "Dear customer, your AMC {{contract_number}} expires on {{end_date}}..."),
    (ev.PAYMENT_DUE, NotificationChannel.EMAIL,
     "Invoice {{invoice_number}} payment due",
     "Invoice {{invoice_number}} of ₹{{amount_due}} is due on {{due_date}}."),
    (ev.SLA_BREACH,  NotificationChannel.IN_APP,
     "Ticket {{ticket_number}} SLA breached",
     "Ticket {{ticket_number}} ({{priority}}) has breached its SLA."),
    # ...one row per event the product sends.
]
```
> Keep placeholders consistent with the `context=` dicts in `workers/tasks.py` and
> the service call sites, so `NotificationService._render` substitutes correctly.

---

## Step 3 — Provisioning service

### `backend/app/services/provisioning.py` (new)
Single entry point that composes tenant + admin + defaults in one transaction.
Reuses Phase 1's trial defaulting and the existing audit + RLS helpers.
```python
import secrets
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.models.notification import NotificationTemplate
from app.core.security import hash_password
from app.services import audit as audit_service
from app.services.tenant import _set_rls, create_tenant   # reuse existing helpers
from app.services.notification_templates import DEFAULT_TEMPLATES

DEFAULT_BRANDING = {"primary_color": "#1677ff", "logo_url": None}
DEFAULT_SETTINGS = {"timezone": "Asia/Kolkata", "currency": "INR"}


@dataclass
class ProvisionResult:
    tenant: Tenant
    first_admin: Optional[User]
    temp_password: Optional[str]   # returned ONCE; never persisted/audited in clear


async def provision_tenant(db: AsyncSession, payload, actor_user_id: UUID | None) -> ProvisionResult:
    # 1. Tenant (reuses create_tenant: slug-uniqueness, trial_ends_at, audit).
    tenant = await create_tenant(db, payload.tenant, actor_user_id=actor_user_id)

    # 2. Default branding/settings (only fill what the admin didn't set).
    tenant.branding = {**DEFAULT_BRANDING, **(tenant.branding or {})}
    tenant.settings = {**DEFAULT_SETTINGS, **(tenant.settings or {})}
    await db.flush()

    await _set_rls(db, tenant.id)  # required before inserting tenant-scoped rows

    # 3. First admin user (optional — back-compat when not supplied).
    first_admin, temp_password = None, None
    if payload.admin_email:
        exists = (await db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == payload.admin_email)
        )).scalar_one_or_none()
        if exists:
            raise HTTPException(status.HTTP_409_CONFLICT, "Admin email already exists")
        temp_password = payload.admin_password or secrets.token_urlsafe(12)
        first_admin = User(
            tenant_id=tenant.id, email=payload.admin_email,
            full_name=payload.admin_full_name or payload.admin_email,
            hashed_password=hash_password(temp_password),
            role=TenantRole.ADMIN, is_active=True,
            must_change_password=(payload.admin_password is None),
        )
        db.add(first_admin)
        await db.flush()
        await audit_service.write_audit(
            db, tenant.id, "user", first_admin.id, "create",
            before=None, after={"email": first_admin.email, "role": "admin"},  # no password
            actor_user_id=actor_user_id)

    # 4. Seed default notification templates (idempotent).
    await _seed_templates(db, tenant.id)

    return ProvisionResult(tenant=tenant, first_admin=first_admin, temp_password=temp_password)


async def _seed_templates(db: AsyncSession, tenant_id: UUID) -> int:
    existing = {(t.event_type, t.channel) for t in (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.tenant_id == tenant_id)
    )).scalars().all()}
    n = 0
    for event_type, channel, subject, body in DEFAULT_TEMPLATES:
        if (event_type, channel) in existing:
            continue
        db.add(NotificationTemplate(tenant_id=tenant_id, event_type=event_type,
                                    channel=channel, subject=subject, body=body, is_active=True))
        n += 1
    await db.flush()
    return n
```
> Note: `create_tenant` already writes the tenant audit row and sets RLS for it.
> We re-assert `_set_rls` before inserting the admin/templates because those are
> separate tenant-scoped INSERTs that must pass the RLS `WITH CHECK` policy.

---

## Step 4 — Schemas

### `backend/app/schemas/tenant.py`
Add a provisioning request that wraps the existing `TenantCreate`, plus a response
that surfaces the one-time credentials:
```python
class TenantProvisionRequest(BaseModel):
    tenant: TenantCreate
    admin_email: Optional[EmailStr] = None
    admin_full_name: Optional[str] = None
    admin_password: Optional[str] = None   # omit → system generates a temp one

class ProvisionedAdmin(BaseModel):
    id: UUID
    email: str
    must_change_password: bool

class TenantProvisionResponse(BaseModel):
    tenant: TenantResponse
    first_admin: Optional[ProvisionedAdmin] = None
    temp_password: Optional[str] = None     # shown ONCE in the UI; not retrievable later
```
(import `EmailStr` from pydantic.)

---

## Step 5 — API endpoint

### `backend/app/api/v1/tenants.py`
Add a provisioning route alongside the existing `POST ""` (leave the old one as-is
for back-compat / existing tests):
```python
@router.post("/provision", response_model=TenantProvisionResponse, status_code=201)
async def provision_tenant_endpoint(
    payload: TenantProvisionRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_platform_admin),
):
    from app.services.provisioning import provision_tenant
    result = await provision_tenant(db, payload, actor_user_id=user.user_id)
    return TenantProvisionResponse(
        tenant=result.tenant,
        first_admin=(ProvisionedAdmin(
            id=result.first_admin.id, email=result.first_admin.email,
            must_change_password=result.first_admin.must_change_password)
            if result.first_admin else None),
        temp_password=result.temp_password,
    )
```

---

## Step 6 — Forced password reset

### 6a. `backend/app/services/auth.py` — surface the flag
In `current_user_info`, add `"must_change_password": user.must_change_password` to
the returned dict (drives the frontend force-reset redirect).

### 6b. `backend/app/api/v1/auth.py` + `services/auth.py` — change-password endpoint
```python
# schema
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# router
@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, db=Depends(get_db),
                          current_user: CurrentUser = Depends(get_current_user)):
    return await auth_service.change_password(db, current_user.user_id,
                                              payload.current_password, payload.new_password)
```
`auth_service.change_password`: load user, `verify_password(current, hashed)` (401
if wrong), set `hashed_password = hash_password(new)`, `must_change_password = False`,
flush. This lets the freshly-onboarded admin retire the temp password.

> Enforcement stance: the reset is **frontend-enforced** (redirect while
> `must_change_password` is true). A hard backend block on other endpoints until
> reset is out of scope for Phase 2 (note for later hardening).

---

## Step 7 — Frontend: onboarding wizard + forced reset

### 7a. `frontend/src/pages/platform/TenantsPage.tsx`
The "Onboard Tenant" modal already POSTs `/tenants`. Extend it:
- Add fields: **Admin Full Name**, **Admin Email**, optional **Admin Password**.
- Submit to `POST /tenants/provision` with `{ tenant: {name,slug,plan,gstin,invoice_prefix}, admin_email, admin_full_name, admin_password }`.
- On success, if `temp_password` is returned, open a **result modal** showing the
  admin email + temp password with a copy button and "won't be shown again" warning,
  instead of just `message.success`.

### 7b. `frontend/src/pages/ForceChangePassword.tsx` (new) + routing in `App.tsx`
- After login, the auth bootstrap (wherever `/auth/me` is consumed, e.g. the auth
  slice/`authSlice`) reads `must_change_password`. When true, route the user to
  `/force-password-change` and block app routes until it's cleared.
- The screen posts `/auth/change-password`; on success it refreshes `/auth/me`
  (flag now false) and proceeds to `/dashboard`.

---

## Step 8 — Tests

### 8a. Unit — `tests/backend/unit/test_provisioning_logic.py`
- `DEFAULT_TEMPLATES` well-formed: every entry is a 4-tuple, channel ∈ NotificationChannel,
  body non-empty; no duplicate (event_type, channel) pairs.
- Temp password generation produces distinct, sufficiently long strings.
- `must_change_password` defaults to False on a plain `User`.

### 8b. Integration — `tests/backend/integration/test_provisioning.py`
- `POST /tenants/provision` (platform auth) with admin fields → 201; response has
  `tenant`, `first_admin.must_change_password == True`, and a non-null `temp_password`.
- The new admin can `POST /auth/login` with the temp password (200).
- `GET /auth/me` shows `must_change_password == True`.
- `POST /auth/change-password` (correct current) → 200; afterwards `/auth/me` shows
  `False`, login with the **old** temp password fails (401), new password works (200).
- Templates seeded: a `NotificationService(db, tenant_id).send(AMC_EXPIRY, ...)` log
  uses the seeded subject (not the generic fallback). Re-provision is idempotent
  (no duplicate templates).
- Back-compat: `POST /tenants` (no admin fields) still 201 and creates no admin.

### 8c. E2E (API-level) — `tests/backend/e2e/test_provisioning_e2e.py`
Full journey: platform admin provisions company → new admin logs in with temp
password → `/auth/me` flags reset → change-password → logs in fresh → reaches an
authenticated endpoint (e.g. `GET /api/v1/customers` 200).

### 8d. Frontend E2E (Playwright, env-guarded) — `tests/frontend/e2e/onboarding.spec.ts`
As platform admin: open Onboard Tenant, fill company + admin, submit, assert the
temp-password result modal appears. Skips unless `E2E_PLATFORM_*` creds are set
(matches the existing guarded-spec convention).

---

## Step 9 — Run & verify

```bash
cd backend && alembic upgrade head            # applies 014
cd tests/backend && ../../backend/venv/bin/python -m pytest -q   # all green incl. new
```

## File change checklist

| # | File | Change |
|---|---|---|
| 1 | `backend/app/models/user.py` | `must_change_password` column |
| 2 | `backend/migrations/versions/014_user_must_change_password.py` | **new** migration |
| 3 | `backend/app/services/notification_templates.py` | **new** default template catalogue |
| 4 | `backend/app/services/provisioning.py` | **new** provisioning service |
| 5 | `backend/app/schemas/tenant.py` | provision request/response schemas |
| 6 | `backend/app/api/v1/tenants.py` | `POST /tenants/provision` |
| 7 | `backend/app/services/auth.py` | surface flag in `current_user_info`; `change_password` |
| 8 | `backend/app/api/v1/auth.py` | `POST /auth/change-password` + schema |
| 9 | `frontend/src/pages/platform/TenantsPage.tsx` | wizard fields + temp-password result modal |
| 10 | `frontend/src/pages/ForceChangePassword.tsx` + `App.tsx` | forced-reset screen + routing |
| 11 | `tests/backend/unit/test_provisioning_logic.py` | **new** |
| 12 | `tests/backend/integration/test_provisioning.py` | **new** |
| 13 | `tests/backend/e2e/test_provisioning_e2e.py` | **new** |
| 14 | `tests/frontend/e2e/onboarding.spec.ts` | **new** (guarded) |

## Out of scope (later phases / explicit non-goals)

- **Self-service signup** — sales-led only (platform admin provisions). No public route.
- **Per-tenant DB `Role` seeding & custom-RBAC editor UI** — default matrix already
  works; defer until tenants need in-app role customisation.
- **Invite-email flow** — optional enhancement: instead of returning a temp password,
  email a signed setup link. Requires reusing the SMTP path in `workers/tasks.py` and
  a short-lived token; the `must_change_password` machinery here is compatible with it.
- **Hard backend block** on non-reset users (reset is frontend-enforced in Phase 2).
- **Branding application in the app shell** (logo/colours) — that's Phase 3 white-label.
