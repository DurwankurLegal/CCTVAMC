"""
Integration tests — Tenant lifecycle enforcement (Phase 1)
===========================================================
A suspended / cancelled / expired-trial tenant must not be able to log in or
refresh tokens. Platform admins are exempt. Reactivation restores access.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from app.core.security import hash_password
from app.models.user import User, TenantRole
from app.models.tenant import Tenant


async def _make_tenant(db, *, slug, status="active", is_active=True, trial_ends_at=None):
    t = Tenant(
        id=uuid.uuid4(), name=f"Co {slug}", slug=slug,
        plan="growth", status=status, is_active=is_active,
        trial_ends_at=trial_ends_at,
    )
    db.add(t)
    await db.flush()
    return t


async def _make_user(db, tenant, email, password="Pass@1234"):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email=email,
        full_name="Lifecycle User", hashed_password=hash_password(password),
        role=TenantRole.ADMIN, is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _login(client, tenant, email, password="Pass@1234"):
    return await client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "tenant_slug": tenant.slug,
    })


# ── Login blocking ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suspended_tenant_login_blocked(client, db):
    t = await _make_tenant(db, slug="susp-co", status="suspended", is_active=False)
    await _make_user(db, t, "susp@test.com")
    r = await _login(client, t, "susp@test.com")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cancelled_tenant_login_blocked(client, db):
    t = await _make_tenant(db, slug="canc-co", status="cancelled", is_active=False)
    await _make_user(db, t, "canc@test.com")
    r = await _login(client, t, "canc@test.com")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_expired_trial_login_blocked(client, db):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    t = await _make_tenant(db, slug="trial-exp", status="trial", trial_ends_at=past)
    await _make_user(db, t, "trialexp@test.com")
    r = await _login(client, t, "trialexp@test.com")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_active_trial_login_allowed(client, db):
    future = datetime.now(timezone.utc) + timedelta(days=5)
    t = await _make_tenant(db, slug="trial-ok", status="trial", trial_ends_at=future)
    await _make_user(db, t, "trialok@test.com")
    r = await _login(client, t, "trialok@test.com")
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_active_tenant_login_allowed(client, db):
    t = await _make_tenant(db, slug="active-co", status="active")
    await _make_user(db, t, "active@test.com")
    r = await _login(client, t, "active@test.com")
    assert r.status_code == 200


# ── Refresh blocking ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_blocked_after_suspend(client, db):
    t = await _make_tenant(db, slug="refresh-susp", status="active")
    await _make_user(db, t, "refsusp@test.com")
    login_r = await _login(client, t, "refsusp@test.com")
    assert login_r.status_code == 200
    refresh_token = login_r.json()["refresh_token"]

    # Suspend the tenant, then attempt to mint fresh tokens.
    t.status = "suspended"
    t.is_active = False
    await db.flush()

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 403


# ── Platform admin exemption ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_admin_login_exempt(client, db):
    """A platform-admin user bypasses tenant-status gating — even when its own
    tenant is suspended (platform admins manage tenants across the platform)."""
    t = await _make_tenant(db, slug="plat-susp", status="suspended", is_active=False)
    u = User(
        id=uuid.uuid4(), tenant_id=t.id, email="plat@test.com",
        full_name="Platform Admin", hashed_password=hash_password("Pass@1234"),
        role=TenantRole.ADMIN, is_active=True, is_platform_admin=True,
    )
    db.add(u)
    await db.flush()
    r = await client.post("/api/v1/auth/login", json={
        "email": "plat@test.com", "password": "Pass@1234", "tenant_slug": t.slug,
    })
    assert r.status_code == 200
