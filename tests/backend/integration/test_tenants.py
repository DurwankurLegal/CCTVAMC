"""
Integration tests — Tenants API (Platform Admin)
==================================================
Covers: create tenant, list, get, update, suspend/activate/cancel,
        slug uniqueness, tenant usage, platform metrics, auth guard.
"""
import uuid
import pytest


BASE = "/api/v1/tenants"


async def _platform_admin_token(client, db) -> str:
    """Mint a platform-admin JWT.

    Authorization for the tenants API is JWT-only (``require_platform_admin``
    decodes the token; it never loads the user from the DB), so we deliberately
    do NOT insert a User row here — a platform admin has no tenant_id and the
    users table enforces tenant_id NOT NULL.
    """
    from app.core.security import create_access_token
    return create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": None,
        "role": "admin",
        "is_platform_admin": True,
    })


TENANT_PAYLOAD = {
    "name": "Demo Corp",
    "slug": "demo-corp",
    "plan": "starter",
}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tenants_requires_auth(client):
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_tenants_requires_platform_admin(client, auth_headers):
    """Regular admin must not access platform tenant list."""
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 403


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tenant_success(client, db):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.post(BASE, json=TENANT_PAYLOAD, headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "demo-corp"
    assert body["plan"] == "starter"


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug_returns_409(client, db):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    await client.post(BASE, json=TENANT_PAYLOAD, headers=headers)
    r = await client.post(BASE, json=TENANT_PAYLOAD, headers=headers)
    assert r.status_code == 409


# ── List & Get ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tenants_returns_created(client, db):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    await client.post(BASE, json=TENANT_PAYLOAD, headers=headers)
    r = await client.get(BASE, headers=headers)
    assert r.status_code == 200
    names = [t["slug"] for t in r.json()]
    assert "demo-corp" in names


@pytest.mark.asyncio
async def test_get_tenant_by_id(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.get(f"{BASE}/{tenant.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_get_nonexistent_tenant_returns_404(client, db):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_tenant_name(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.patch(f"{BASE}/{tenant.id}", json={"name": "Updated Corp"},
                           headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Corp"


# ── Status lifecycle ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suspend_tenant(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.post(f"{BASE}/{tenant.id}/suspend", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"


@pytest.mark.asyncio
async def test_activate_tenant(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    # First suspend, then activate
    await client.post(f"{BASE}/{tenant.id}/suspend", headers=headers)
    r = await client.post(f"{BASE}/{tenant.id}/activate", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "active"


@pytest.mark.asyncio
async def test_cancel_tenant(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.post(f"{BASE}/{tenant.id}/cancel", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


# ── Usage & metrics ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_usage_endpoint(client, db, tenant):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.get(f"{BASE}/{tenant.id}/usage", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "users" in body
    assert "sites" in body
    assert "plan" in body


@pytest.mark.asyncio
async def test_platform_metrics_endpoint(client, db):
    tok = await _platform_admin_token(client, db)
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.get("/api/v1/tenants/platform/metrics", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "total_tenants" in body
    assert "by_plan" in body
