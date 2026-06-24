"""
End-to-end tests — Phase 1 tenant lifecycle (API-level, full request cycle)
===========================================================================
These drive complete journeys through the real ASGI app across the auth and
tenants routers together — the same HTTP contract a client uses — without a live
server. They complement the focused integration tests by exercising the whole
suspend → blocked → reactivate and trial → expire → blocked flows.

(Tenant + first admin are seeded directly because self-service provisioning is a
later phase; everything after that goes through HTTP / service entry points.)
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from app.core.security import hash_password
from app.models.user import User, TenantRole
from app.models.tenant import Tenant
from app.services.tenant import run_trial_expiry


async def _seed_tenant_and_admin(db, *, slug, status="active",
                                 is_active=True, trial_ends_at=None,
                                 email=None, password="Pass@1234"):
    t = Tenant(id=uuid.uuid4(), name=f"Co {slug}", slug=slug, plan="growth",
               status=status, is_active=is_active, trial_ends_at=trial_ends_at)
    db.add(t)
    await db.flush()
    u = User(id=uuid.uuid4(), tenant_id=t.id, email=email or f"admin@{slug}.com",
             full_name="Admin", hashed_password=hash_password(password),
             role=TenantRole.ADMIN, is_active=True)
    db.add(u)
    await db.flush()
    return t, u


async def _login(client, slug, email, password="Pass@1234"):
    return await client.post("/api/v1/auth/login",
                             json={"email": email, "password": password, "tenant_slug": slug})


# ── Journey 1: full suspend → blocked → reactivate lifecycle ──────────────────

@pytest.mark.asyncio
async def test_e2e_suspend_then_reactivate_lifecycle(client, db, platform_headers):
    t, u = await _seed_tenant_and_admin(db, slug="lifecycle-co")

    # 1. Active tenant: login + authenticated identity call both succeed.
    login_r = await _login(client, t.slug, u.email)
    assert login_r.status_code == 200
    tokens = login_r.json()
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == u.email

    # 2. Platform admin suspends the tenant.
    susp = await client.post(f"/api/v1/tenants/{t.id}/suspend", headers=platform_headers)
    assert susp.status_code == 200
    assert susp.json()["status"] == "suspended"

    # 3. Login is now blocked, and the existing refresh token cannot mint new ones.
    assert (await _login(client, t.slug, u.email)).status_code == 403
    refresh_r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert refresh_r.status_code == 403

    # 4. Platform admin reactivates → login works again.
    act = await client.post(f"/api/v1/tenants/{t.id}/activate", headers=platform_headers)
    assert act.status_code == 200
    assert act.json()["status"] == "active"
    assert (await _login(client, t.slug, u.email)).status_code == 200


# ── Journey 2: cancellation is terminal for login ─────────────────────────────

@pytest.mark.asyncio
async def test_e2e_cancelled_tenant_cannot_login(client, db, platform_headers):
    t, u = await _seed_tenant_and_admin(db, slug="cancel-co")
    assert (await _login(client, t.slug, u.email)).status_code == 200

    cancel = await client.post(f"/api/v1/tenants/{t.id}/cancel", headers=platform_headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    blocked = await _login(client, t.slug, u.email)
    assert blocked.status_code == 403
    assert "not active" in blocked.json()["detail"]


# ── Journey 3: trial expiry sweep → blocked, status visible to platform ───────

@pytest.mark.asyncio
async def test_e2e_trial_expiry_sweep_blocks_login(client, db, platform_headers):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    t, u = await _seed_tenant_and_admin(db, slug="trial-co", status="trial",
                                        trial_ends_at=past)

    # Gate blocks an expired trial even before the sweep runs (defence in depth).
    assert (await _login(client, t.slug, u.email)).status_code == 403

    # The daily sweep transitions it to suspended.
    suspended = await run_trial_expiry(db)
    assert suspended == 1

    # Platform admin sees the suspended status, and login stays blocked.
    got = await client.get(f"/api/v1/tenants/{t.id}", headers=platform_headers)
    assert got.status_code == 200
    body = got.json()
    assert body["status"] == "suspended"
    assert body["is_active"] is False
    assert (await _login(client, t.slug, u.email)).status_code == 403


# ── Journey 4: active trial works end to end ──────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_active_trial_full_access(client, db):
    future = datetime.now(timezone.utc) + timedelta(days=7)
    t, u = await _seed_tenant_and_admin(db, slug="trial-active-co", status="trial",
                                        trial_ends_at=future)
    login_r = await _login(client, t.slug, u.email)
    assert login_r.status_code == 200
    access = login_r.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
