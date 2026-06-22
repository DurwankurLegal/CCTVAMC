"""Granular RBAC: default matrix + custom DB roles are enforced."""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, TenantRole
from app.models.rbac import Role, Permission, RolePermission, UserRole
from app.core.security import hash_password, create_access_token


def _token(user, tenant):
    return create_access_token({
        "sub": str(user.id), "tenant_id": str(tenant.id),
        "role": user.role, "is_platform_admin": False,
    })


@pytest.mark.asyncio
async def test_viewer_role_denied_write(client: AsyncClient, db: AsyncSession, tenant):
    viewer = User(id=uuid4(), tenant_id=tenant.id, email="viewer@test.com",
                  full_name="Viewer", hashed_password=hash_password("x"),
                  role=TenantRole.VIEWER)
    db.add(viewer)
    await db.flush()
    resp = await client.post(
        "/api/v1/customers", json={"name": "X", "category": "commercial"},
        headers={"Authorization": f"Bearer {_token(viewer, tenant)}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_custom_db_role_grants_only_listed_permissions(client: AsyncClient, db: AsyncSession, tenant):
    # User whose legacy role would normally allow nothing, but a custom DB role
    # grants exactly customers:read (no write).
    user = User(id=uuid4(), tenant_id=tenant.id, email="custom@test.com",
                full_name="Custom", hashed_password=hash_password("x"),
                role=TenantRole.VIEWER)
    role = Role(id=uuid4(), tenant_id=tenant.id, name="ReadOnlyCustomers")
    perm = (await db.execute(
        __import__("sqlalchemy").select(Permission).where(Permission.code == "customers:read")
    )).scalar_one_or_none()
    if perm is None:  # SQLite harness has no seeded permissions; create it
        perm = Permission(id=uuid4(), code="customers:read", description="read customers")
        db.add(perm)
    db.add_all([user, role])
    await db.flush()
    db.add(RolePermission(id=uuid4(), role_id=role.id, permission_id=perm.id))
    db.add(UserRole(id=uuid4(), tenant_id=tenant.id, user_id=user.id, role_id=role.id))
    await db.flush()

    headers = {"Authorization": f"Bearer {_token(user, tenant)}"}
    # read allowed
    assert (await client.get("/api/v1/customers", headers=headers)).status_code == 200
    # write denied (custom role has no customers:write)
    resp = await client.post("/api/v1/customers", json={"name": "Y", "category": "commercial"}, headers=headers)
    assert resp.status_code == 403
