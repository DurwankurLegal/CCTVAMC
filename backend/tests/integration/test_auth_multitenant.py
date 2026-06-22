"""Login is tenant-scoped (duplicate cross-tenant emails) and refresh rotates."""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_duplicate_email_across_tenants_requires_slug(client: AsyncClient, db: AsyncSession, admin_user):
    # admin_user already exists as admin@test.com in the default tenant.
    other = Tenant(id=uuid4(), name="Other", slug="other-co")
    db.add(other)
    await db.flush()
    db.add(User(
        id=uuid4(), tenant_id=other.id, email="admin@test.com", full_name="Other Admin",
        hashed_password=hash_password("password123"), role=TenantRole.ADMIN,
    ))
    await db.flush()

    # Ambiguous login (no slug) → 400.
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123",
    })
    assert resp.status_code == 400

    # Disambiguated by slug → 200.
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123", "tenant_slug": "other-co",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_token(client: AsyncClient, admin_user, tenant):
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123",
    })
    old_refresh = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200

    # Reusing the now-rotated token must be rejected.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
