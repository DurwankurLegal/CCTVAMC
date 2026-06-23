"""Step 4.1 — User & RBAC administration: roles catalogue, /auth/me permissions,
and create/role-change/deactivate flow with permission gating."""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, TenantRole
from app.core.security import hash_password, create_access_token


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
def viewer_token(tenant) -> str:
    return create_access_token({
        "sub": str(uuid.uuid4()), "tenant_id": str(tenant.id),
        "role": "viewer", "is_platform_admin": False,
    })


@pytest.mark.asyncio
async def test_auth_me_includes_permissions(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/auth/me", headers=_auth(admin_token))
    assert resp.status_code == 200
    perms = resp.json()["permissions"]
    # Admin has the full matrix, including user management.
    assert "users:write" in perms and "customers:read" in perms


@pytest.mark.asyncio
async def test_roles_catalogue(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/users/roles", headers=_auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    keys = [r["key"] for r in body["roles"]]
    assert {"admin", "manager", "technician", "viewer"}.issubset(set(keys))
    tech = next(r for r in body["roles"] if r["key"] == "technician")
    assert "engineer_visits:write" in tech["permissions"]
    assert "users:write" not in tech["permissions"]


@pytest.mark.asyncio
async def test_viewer_cannot_manage_users(client: AsyncClient, viewer_token: str):
    assert (await client.get("/api/v1/users/roles", headers=_auth(viewer_token))).status_code == 403
    assert (await client.post("/api/v1/users", headers=_auth(viewer_token),
            json={"email": "x@y.com", "full_name": "X", "password": "password123", "role": "viewer"})).status_code == 403


@pytest.mark.asyncio
async def test_admin_user_lifecycle(client: AsyncClient, admin_token: str):
    email = f"new-{uuid.uuid4().hex[:8]}@test.com"
    created = await client.post("/api/v1/users", headers=_auth(admin_token),
                                json={"email": email, "full_name": "New Staff",
                                      "password": "password123", "role": "technician"})
    assert created.status_code == 201, created.text
    uid = created.json()["id"]
    assert created.json()["role"] == "technician"

    # Change role
    upd = await client.patch(f"/api/v1/users/{uid}", headers=_auth(admin_token),
                             json={"role": "coordinator"})
    assert upd.status_code == 200 and upd.json()["role"] == "coordinator"

    # Deactivate
    deact = await client.patch(f"/api/v1/users/{uid}", headers=_auth(admin_token),
                               json={"is_active": False})
    assert deact.status_code == 200 and deact.json()["is_active"] is False
