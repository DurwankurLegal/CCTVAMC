# Phase 1 — Tenant Lifecycle Enforcement: File-Level Implementation Spec

> Status: Spec only — not yet implemented.
> Parent plan: `Docs/phase2-multitenant-saas-plan.md`
> Date: 2026-06-24

## Goal

Close the live security gap: a **suspended / cancelled / trial-expired** tenant's users can
currently still log in and use the app (login & refresh check only `User.is_active`, never
`tenant.status`). Also finish wiring plan-limit enforcement.

## Design decisions

- **Where to enforce status:** in `login()` **and** `refresh()` — both already hit the DB for the
  user, so no extra round-trip. This bounds a suspended tenant to at most one access-token lifetime
  (default 15 min) with no new tokens issuable. Per-request enforcement in `get_current_user` is
  **out of scope** for Phase 1 (would add a DB hit to every request); noted as optional hardening below.
- **Platform admins** (`tenant_id is None`, `is_platform_admin=True`) bypass tenant-status checks.
- **Trial expiry:** stored as `tenant.trial_ends_at`; a daily Celery beat job transitions expired
  trials to `SUSPENDED` and the login check also treats `TRIAL` past `trial_ends_at` as blocked
  (defence in depth — enforced even if the job hasn't run yet).
- **Limits:** `enforce_limit(..., "technicians")` is wired into `create_user` when role is technician.
  **Sites have no creation path in the codebase yet** (`CustomerSite` is defined but never instantiated),
  so site enforcement is a documented forward-hook, not code in this phase.

---

## Step 1 — Data model: add `trial_ends_at` to Tenant

### 1a. `backend/app/models/tenant.py`
Add to the `Tenant` model (alongside `status`):
```python
from datetime import datetime
from sqlalchemy import DateTime
# ...
trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
Add a helper near the bottom of the module (used by login + the Celery job):
```python
TRIAL_PERIOD_DAYS = 14
```

### 1b. New migration `backend/migrations/versions/013_tenant_trial_ends_at.py`
Follow the style of `009_tenant_subscription.py`. `down_revision = "012"` (current head).
```python
revision = "013"
down_revision = "012"

def upgrade() -> None:
    op.add_column("tenants", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    # Backfill: existing TRIAL tenants get a window from now; active ones stay null.
    op.execute(
        "UPDATE tenants SET trial_ends_at = now() + interval '14 days' "
        "WHERE status = 'trial' AND trial_ends_at IS NULL"
    )

def downgrade() -> None:
    op.drop_column("tenants", "trial_ends_at")
```

### 1c. `backend/app/services/tenant.py` — set `trial_ends_at` on creation
In `create_tenant`, after building the `Tenant` and before flush, default the trial window when the
tenant is created in TRIAL status:
```python
from datetime import datetime, timezone, timedelta
from app.models.tenant import TRIAL_PERIOD_DAYS
# ...
tenant = Tenant(**payload.model_dump())
if tenant.status == TenantStatus.TRIAL.value and tenant.trial_ends_at is None:
    tenant.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=TRIAL_PERIOD_DAYS)
```

### 1d. `backend/app/schemas/tenant.py` — expose it
Add to `TenantResponse`:
```python
trial_ends_at: Optional[datetime] = None
```
(import `datetime`). Optionally allow platform admin to set/extend it via `TenantUpdate`:
```python
trial_ends_at: Optional[datetime] = None
```

---

## Step 2 — Enforce tenant status at login & refresh

### 2a. `backend/app/services/auth.py` — shared guard
Add a helper (after imports), reused by `login` and `refresh`:
```python
from datetime import datetime, timezone
from app.models.tenant import TenantStatus

async def _assert_tenant_usable(db: AsyncSession, tenant_id: Optional[UUID]) -> None:
    """Block login/refresh for tenants that are suspended, cancelled, or past trial.
    Platform-admin users have tenant_id=None and are exempt."""
    if tenant_id is None:
        return
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if tenant.status in (TenantStatus.SUSPENDED.value, TenantStatus.CANCELLED.value) or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This workspace is not active. Contact your administrator.")
    if (tenant.status == TenantStatus.TRIAL.value and tenant.trial_ends_at
            and tenant.trial_ends_at < datetime.now(timezone.utc)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Trial period has ended. Contact your administrator.")
```

### 2b. Call it in `login()`
After the user/password (and 2FA) checks pass, before `_issue_tokens`:
```python
await _assert_tenant_usable(db, user.tenant_id)
return await _issue_tokens(db, user)
```

### 2c. Call it in `refresh()`
After loading `user` (the `select(User)... is_active == True` block), before rotating/issuing:
```python
await _assert_tenant_usable(db, user.tenant_id)
session.revoked = True
...
```
This stops a suspended tenant from minting fresh access tokens once the current one expires.

### 2d. (Optional, deferred) per-request enforcement
If near-instant cutoff is later required, add a dependency that checks `tenant.status` with a short
Redis cache (e.g. 60s TTL) and layer it onto routers. Not in Phase 1.

---

## Step 3 — Wire plan-limit enforcement for technicians

### `backend/app/services/user.py` — `create_user`
Technicians are `User` rows with `role == TenantRole.TECHNICIAN`. Currently only the `"users"` limit
is enforced. Add the technician check immediately after it:
```python
from app.services.tenant import enforce_limit
from app.models.user import TenantRole

await enforce_limit(db, tenant_id, "users")
if payload.role == TenantRole.TECHNICIAN.value:
    await enforce_limit(db, tenant_id, "technicians")
```
`enforce_limit` already supports the `"technicians"` resource (`services/tenant.py:186`). No change there.

### Sites — forward-hook only (no code this phase)
`CustomerSite` has no create endpoint/service today. When one is added (Phase 3 work or sooner),
call `await enforce_limit(db, tenant_id, "sites")` at the start of that creation service. Leave a
`# TODO(limits)` note in the future site-creation service. Tracked here so it isn't missed.

---

## Step 4 — Daily trial-expiry Celery job

### 4a. `backend/app/workers/tasks.py` — new task
Add alongside the other `@celery_app.task` jobs:
```python
@celery_app.task
def expire_trials():
    """Suspend tenants whose trial window has elapsed (Phase 1 lifecycle)."""
    import asyncio

    async def _run():
        from sqlalchemy import select
        from datetime import datetime, timezone
        from app.models.tenant import Tenant, TenantStatus

        SessionFactory = _get_session_factory()
        async with SessionFactory() as db:
            now = datetime.now(timezone.utc)
            rows = (await db.execute(
                select(Tenant).where(
                    Tenant.status == TenantStatus.TRIAL.value,
                    Tenant.trial_ends_at.is_not(None),
                    Tenant.trial_ends_at < now,
                )
            )).scalars().all()
            for t in rows:
                t.status = TenantStatus.SUSPENDED.value
                t.is_active = False
                logger.info("Trial expired; tenant suspended", tenant_id=str(t.id))
            await db.commit()
            logger.info("Trial expiry sweep complete", suspended=len(rows))

    asyncio.run(_run())
```
> Note: this writes tenant status directly (matching the existing job style). If you want the
> transition on the tenant's audit chain, call `tenant_service.set_tenant_status(db, t.id, "suspend")`
> per row instead (sets RLS + writes an audit row). Recommended for consistency with manual suspends.

### 4b. `backend/app/workers/celery_app.py` — schedule it
Add to `beat_schedule`:
```python
"expire-trials": {
    "task": "app.workers.tasks.expire_trials",
    "schedule": 86400.0,  # daily
},
```

---

## Step 5 — Tests

Test root per project convention: `tests/backend/`. Fixtures (`client`, `auth_headers`,
`platform_headers`, `tenant`, `admin_user`) live in `tests/backend/conftest.py`.

### 5a. `tests/backend/integration/test_tenant_lifecycle.py` (new)
- **suspended login blocked:** platform-admin suspends a tenant via `POST /tenants/{id}/suspend`;
  a user in that tenant then `POST /auth/login` → expect **403**.
- **cancelled login blocked:** same via `/cancel` → **403**.
- **reactivation restores login:** `/activate` → login succeeds again (200, tokens returned).
- **expired-trial login blocked:** set `trial_ends_at` in the past on a TRIAL tenant → login → **403**.
- **refresh blocked after suspend:** login (get refresh token) → suspend tenant → `POST /auth/refresh`
  → **403**.
- **platform admin exempt:** platform-admin login works regardless of any tenant status.

### 5b. `tests/backend/integration/test_plan_limits.py` (extend or new)
- **technician limit:** on a `starter` tenant (max_technicians=3), create 3 technician users (201),
  the 4th → **403** with the "Plan limit reached for technicians" detail.
- **user limit unaffected by role mix** sanity check (existing users-limit test stays green).

### 5c. `tests/backend/unit/test_trial_expiry.py` (new)
- Seed a TRIAL tenant with `trial_ends_at` in the past + one with a future date; run `expire_trials`
  (call the inner async `_run`, or refactor logic into a plain async fn `_expire_trials(db)` the task
  wraps, so it's unit-testable on the SQLite session). Assert the past one is `SUSPENDED`/`is_active=False`
  and the future one is untouched.

> Refactor tip: extract `expire_trials`' body into `async def run_trial_expiry(db)` in a service
> (e.g. `services/tenant.py`) and have the Celery task call it. Keeps the task a thin wrapper and the
> logic directly testable without Celery/asyncio plumbing — matches how other logic is structured.

---

## Step 6 — Run & verify

```bash
# migrations
cd backend && alembic upgrade head
# backend tests
cd tests/backend && ../../backend/venv/bin/python -m pytest -q
```
Expect: new lifecycle + limit tests pass; existing 312 backend tests stay green.

---

## File change checklist

| # | File | Change |
|---|---|---|
| 1 | `backend/app/models/tenant.py` | add `trial_ends_at` column + `TRIAL_PERIOD_DAYS` |
| 2 | `backend/migrations/versions/013_tenant_trial_ends_at.py` | **new** migration (add col + backfill) |
| 3 | `backend/app/services/tenant.py` | default `trial_ends_at` in `create_tenant`; (opt) `run_trial_expiry` |
| 4 | `backend/app/schemas/tenant.py` | expose `trial_ends_at` on response (+opt update) |
| 5 | `backend/app/services/auth.py` | add `_assert_tenant_usable`; call in `login` + `refresh` |
| 6 | `backend/app/services/user.py` | enforce `"technicians"` limit in `create_user` |
| 7 | `backend/app/workers/tasks.py` | add `expire_trials` task |
| 8 | `backend/app/workers/celery_app.py` | schedule `expire-trials` daily |
| 9 | `tests/backend/integration/test_tenant_lifecycle.py` | **new** tests |
| 10 | `tests/backend/integration/test_plan_limits.py` | technician-limit test |
| 11 | `tests/backend/unit/test_trial_expiry.py` | **new** unit test |

## Out of scope (later phases)
- Per-request status enforcement w/ Redis cache (hardening).
- Site-creation path + its limit hook (no create endpoint exists yet).
- Frontend handling of the 403 "workspace not active" → dedicated screen (Phase 3 white-label work).
- Any billing/payment reaction — suspensions remain manual or trial-driven only.
