"""
Integration tests — Authentication flow
=========================================
Covers: POST /api/v1/auth/login, /auth/refresh, /auth/me,
        /auth/2fa/enroll, /auth/2fa/verify, multi-tenant login,
        inactive user rejection, wrong password rejection.
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.models.user import User, TenantRole
from app.models.tenant import Tenant


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_user(db, tenant, email, password, role=TenantRole.ADMIN, active=True):
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        full_name="Test User",
        hashed_password=hash_password(password),
        role=role,
        is_active=active,
    )
    db.add(u)
    await db.flush()
    return u


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client, db, tenant):
    await _create_user(db, tenant, "login@test.com", "Pass@1234")
    r = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "Pass@1234",
        "tenant_slug": tenant.slug,
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password(client, db, tenant):
    await _create_user(db, tenant, "wp@test.com", "Right@1234")
    r = await client.post("/api/v1/auth/login", json={
        "email": "wp@test.com",
        "password": "Wrong@1234",
        "tenant_slug": tenant.slug,
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client, tenant):
    r = await client.post("/api/v1/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "anything",
        "tenant_slug": tenant.slug,
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(client, db, tenant):
    await _create_user(db, tenant, "inactive@test.com", "Pass@1234", active=False)
    r = await client.post("/api/v1/auth/login", json={
        "email": "inactive@test.com",
        "password": "Pass@1234",
        "tenant_slug": tenant.slug,
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_tenant_slug(client, db, tenant):
    await _create_user(db, tenant, "slugtest@test.com", "Pass@1234")
    r = await client.post("/api/v1/auth/login", json={
        "email": "slugtest@test.com",
        "password": "Pass@1234",
        "tenant_slug": "no-such-slug",
    })
    assert r.status_code == 401


# ── /auth/me ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_me_returns_user_info(client, admin_user, auth_headers):
    r = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == admin_user.email
    assert "permissions" in body
    assert "role" in body


@pytest.mark.asyncio
async def test_auth_me_no_token_returns_401(client):
    r = await client.get("/api/v1/auth/me")
    # Regression (OBS-4): missing credentials must be 401 (not HTTPBearer's
    # default 403), with a WWW-Authenticate challenge header.
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_auth_me_bad_token_returns_401(client):
    r = await client.get("/api/v1/auth/me",
                         headers={"Authorization": "Bearer totally.invalid.token"})
    assert r.status_code == 401


# ── Token refresh ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_token_refresh_success(client, db, tenant):
    await _create_user(db, tenant, "refresh@test.com", "Pass@1234")
    login_r = await client.post("/api/v1/auth/login", json={
        "email": "refresh@test.com",
        "password": "Pass@1234",
        "tenant_slug": tenant.slug,
    })
    assert login_r.status_code == 200
    refresh_token = login_r.json()["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_token_refresh_invalid_token(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bad.token.here"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_rotation_revokes_old_token(client, db, tenant):
    """Using a refresh token twice must fail the second time (rotation)."""
    await _create_user(db, tenant, "rotate@test.com", "Pass@1234")
    login_r = await client.post("/api/v1/auth/login", json={
        "email": "rotate@test.com",
        "password": "Pass@1234",
        "tenant_slug": tenant.slug,
    })
    rt = login_r.json()["refresh_token"]
    # First refresh — should succeed
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r1.status_code == 200
    # Second refresh with same token — must be rejected (revoked)
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r2.status_code == 401


# ── 2FA enroll / verify ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2fa_enroll_returns_secret_and_uri(client, auth_headers):
    r = await client.post("/api/v1/auth/2fa/enroll", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "secret" in body
    assert "provisioning_uri" in body


@pytest.mark.asyncio
async def test_2fa_verify_with_valid_code(client, db, admin_user, auth_headers):
    import pyotp
    enroll_r = await client.post("/api/v1/auth/2fa/enroll", headers=auth_headers)
    secret = enroll_r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    r = await client.post("/api/v1/auth/2fa/verify",
                          json={"code": code}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["enabled"] is True


@pytest.mark.asyncio
async def test_2fa_verify_with_invalid_code(client, auth_headers):
    await client.post("/api/v1/auth/2fa/enroll", headers=auth_headers)
    r = await client.post("/api/v1/auth/2fa/verify",
                          json={"code": "000000"}, headers=auth_headers)
    assert r.status_code == 400
