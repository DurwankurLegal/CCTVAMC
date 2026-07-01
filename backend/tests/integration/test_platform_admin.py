"""Platform admin console (Step 2): tenant lifecycle, usage, metrics, and
subscription invoicing. Also asserts tenant admins are denied platform routes.
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, TenantRole
from app.core.security import hash_password, create_access_token


@pytest.fixture
def platform_token(admin_user: User, tenant) -> str:
    # Same identity as admin_user but with the platform-admin flag set.
    return create_access_token({
        "sub": str(admin_user.id),
        "tenant_id": str(tenant.id),
        "role": admin_user.role,
        "is_platform_admin": True,
    })


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_tenant_admin_denied_platform_routes(client: AsyncClient, admin_token: str):
    """A tenant admin (is_platform_admin=False) must not reach platform routes."""
    assert (await client.get("/api/v1/tenants", headers=_auth(admin_token))).status_code == 403
    assert (await client.get("/api/v1/tenants/platform/metrics", headers=_auth(admin_token))).status_code == 403
    create = await client.post("/api/v1/tenants", json={"name": "X", "slug": "x"},
                               headers=_auth(admin_token))
    assert create.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_tenant_lifecycle(client: AsyncClient, platform_token: str):
    # Create
    slug = f"acme-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/api/v1/tenants",
                             json={"name": "Acme Security", "slug": slug, "plan": "starter"},
                             headers=_auth(platform_token))
    assert resp.status_code == 201, resp.text
    tid = resp.json()["id"]

    # Appears in listing
    listed = await client.get("/api/v1/tenants", headers=_auth(platform_token))
    assert listed.status_code == 200
    assert tid in [t["id"] for t in listed.json()]

    # Status filter
    filtered = await client.get("/api/v1/tenants?status=suspended", headers=_auth(platform_token))
    assert tid not in [t["id"] for t in filtered.json()]

    # Suspend → status changes and tenant remains visible (unlike old is_active filter)
    susp = await client.post(f"/api/v1/tenants/{tid}/suspend", headers=_auth(platform_token))
    assert susp.status_code == 200
    assert susp.json()["status"] == "suspended"
    assert susp.json()["is_active"] is False
    susp_list = await client.get("/api/v1/tenants?status=suspended", headers=_auth(platform_token))
    assert tid in [t["id"] for t in susp_list.json()]

    # Activate
    act = await client.post(f"/api/v1/tenants/{tid}/activate", headers=_auth(platform_token))
    assert act.json()["status"] == "active" and act.json()["is_active"] is True

    # Update plan
    upd = await client.patch(f"/api/v1/tenants/{tid}", json={"plan": "growth"},
                             headers=_auth(platform_token))
    assert upd.json()["plan"] == "growth"

    # Usage summary reflects the plan
    usage = await client.get(f"/api/v1/tenants/{tid}/usage", headers=_auth(platform_token))
    assert usage.status_code == 200
    body = usage.json()
    assert body["plan"] == "growth"
    assert body["users"]["limit"] == 25  # growth plan limit


@pytest.mark.asyncio
async def test_subscription_invoice_generation(client: AsyncClient, platform_token: str):
    slug = f"beta-{uuid.uuid4().hex[:8]}"
    tid = (await client.post("/api/v1/tenants",
                             json={"name": "Beta", "slug": slug, "plan": "growth"},
                             headers=_auth(platform_token))).json()["id"]

    gen = await client.post(f"/api/v1/tenants/{tid}/subscription-invoices",
                            json={"period_start": "2026-06-01", "period_end": "2026-06-30"},
                            headers=_auth(platform_token))
    assert gen.status_code == 201, gen.text
    assert gen.json()["plan"] == "growth"
    assert gen.json()["amount"] == 9999.0

    hist = await client.get(f"/api/v1/tenants/{tid}/subscription-invoices",
                            headers=_auth(platform_token))
    assert hist.status_code == 200
    assert len(hist.json()) == 1


@pytest.mark.asyncio
async def test_platform_metrics(client: AsyncClient, platform_token: str):
    resp = await client.get("/api/v1/tenants/platform/metrics", headers=_auth(platform_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "total_tenants" in body
    assert "by_plan" in body and "by_status" in body


# ── Platform Admin: User Management & Password Reset ──────────────────────────

@pytest.mark.asyncio
async def test_platform_admin_list_tenant_users(
    client: AsyncClient, platform_token: str, db: AsyncSession
):
    """Platform admin can list all users for any tenant."""
    # Provision a fresh tenant with an admin user
    slug = f"usr-list-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/tenants/provision",
        json={
            "tenant": {"name": "UserList Tenant", "slug": slug},
            "admin_email": f"adm-{slug}@test.com"
        },
        headers=_auth(platform_token),
    )
    assert resp.status_code == 201, resp.text
    tid = resp.json()["tenant"]["id"]

    users_resp = await client.get(f"/api/v1/tenants/{tid}/users", headers=_auth(platform_token))
    assert users_resp.status_code == 200
    users = users_resp.json()
    # Should have at least the provisioned admin
    assert isinstance(users, list)
    assert len(users) >= 1
    # Each user should have required fields
    for u in users:
        assert "id" in u
        assert "email" in u
        assert "role" in u
        assert "must_change_password" in u


@pytest.mark.asyncio
async def test_platform_admin_reset_tenant_user_password(
    client: AsyncClient, platform_token: str, db: AsyncSession
):
    """Platform admin can force-reset a tenant user's password.
    Verifies temp password is returned once and must_change_password is set True.
    """
    # Provision tenant
    slug = f"pwd-reset-{uuid.uuid4().hex[:8]}"
    provision_resp = await client.post(
        "/api/v1/tenants/provision",
        json={
            "tenant": {"name": "ResetTest Tenant", "slug": slug},
            "admin_email": f"adm-{slug}@test.com"
        },
        headers=_auth(platform_token),
    )
    assert provision_resp.status_code == 201, provision_resp.text
    tid = provision_resp.json()["tenant"]["id"]

    # Get the first user id
    users_resp = await client.get(f"/api/v1/tenants/{tid}/users", headers=_auth(platform_token))
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) >= 1
    uid = users[0]["id"]

    # Reset password
    reset_resp = await client.post(
        f"/api/v1/tenants/{tid}/users/{uid}/reset-password",
        headers=_auth(platform_token),
    )
    assert reset_resp.status_code == 200, reset_resp.text
    body = reset_resp.json()
    assert "temp_password" in body
    assert len(body["temp_password"]) >= 12
    assert body["must_change_password"] is True
    assert body["user_id"] == uid

    # Confirm must_change_password was persisted
    users_after = await client.get(f"/api/v1/tenants/{tid}/users", headers=_auth(platform_token))
    target = next(u for u in users_after.json() if u["id"] == uid)
    assert target["must_change_password"] is True


@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_platform_user_endpoints(
    client: AsyncClient, admin_token: str, tenant
):
    """Regular tenant admin (is_platform_admin=False) must be denied access to
    the platform user-listing and password reset endpoints."""
    tid = str(tenant.id)
    fake_uid = str(uuid.uuid4())

    list_resp = await client.get(f"/api/v1/tenants/{tid}/users", headers=_auth(admin_token))
    assert list_resp.status_code == 403

    reset_resp = await client.post(
        f"/api/v1/tenants/{tid}/users/{fake_uid}/reset-password",
        headers=_auth(admin_token),
    )
    assert reset_resp.status_code == 403
