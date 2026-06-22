"""
Critical security test: Tenant A must NOT be able to read Tenant B's data.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.core.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, db: AsyncSession, admin_token: str):
    # Create a second tenant and user
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b")
    db.add(tenant_b)
    await db.flush()

    user_b = User(
        id=uuid4(),
        tenant_id=tenant_b.id,
        email="admin@tenantb.com",
        full_name="Tenant B Admin",
        hashed_password=hash_password("password123"),
        role=TenantRole.ADMIN,
    )
    db.add(user_b)
    await db.flush()

    token_b = create_access_token({
        "sub": str(user_b.id),
        "tenant_id": str(tenant_b.id),
        "role": user_b.role,
        "is_platform_admin": False,
    })

    # Tenant A creates a customer
    resp = await client.post(
        "/api/v1/customers",
        json={"name": "Tenant A Customer", "category": "commercial"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    customer_a_id = resp.json()["id"]

    # Tenant B tries to list customers — must NOT see Tenant A's customer
    resp_b = await client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
    ids_b = [c["id"] for c in resp_b.json()]
    assert customer_a_id not in ids_b, "Tenant isolation BREACH: Tenant B saw Tenant A's customer!"

    # Tenant B tries to GET Tenant A's customer directly
    resp_direct = await client.get(
        f"/api/v1/customers/{customer_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_direct.status_code == 404, "Tenant isolation BREACH: direct GET returned 200!"
