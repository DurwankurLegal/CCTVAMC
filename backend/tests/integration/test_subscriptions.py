import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.models.user import User
from app.models.subscription import TenantModule, Module, SaasPlan, TenantSubscription
from app.core.security import create_access_token
import uuid
from datetime import datetime, timezone

def _get_token(user: User, tenant: Tenant) -> str:
    return create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": user.role,
        "is_platform_admin": False,
    })

@pytest.mark.asyncio
async def test_legacy_tenant_unrestricted_by_default(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """If a tenant has no entries in the tenant_modules table, it acts as a legacy tenant and defaults to allowing all modules."""
    token = _get_token(admin_user, tenant)
    
    # Try reaching quotations (sales module)
    resp = await client.get("/api/v1/quotations", headers={"Authorization": f"Bearer {token}"})
    # Should not be 402, should be 200 (since it returns empty list or list of quotes)
    assert resp.status_code == 200
    
    # Try reaching rentals (rental module)
    resp2 = await client.get("/api/v1/rentals/contracts", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200

@pytest.mark.asyncio
async def test_module_restricted_if_configured(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """If a tenant has at least one module configured, non-configured modules return 402."""
    # 1. Register the modules in Module master first
    sales_mod = Module(code="sales", name="Sales Management", is_core=False, is_active=True)
    rental_mod = Module(code="rental", name="Rental Management", is_core=False, is_active=True)
    db.add_all([sales_mod, rental_mod])
    await db.flush()

    # 2. Grant only 'sales' to the tenant
    tm = TenantModule(
        tenant_id=tenant.id,
        module_code="sales",
        status="active",
        starts_at=datetime.now(timezone.utc)
    )
    db.add(tm)
    await db.flush()

    token = _get_token(admin_user, tenant)

    # 3. Hit sales quotations endpoint (should be allowed)
    resp = await client.get("/api/v1/quotations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # 4. Hit rental contracts endpoint (should be blocked)
    resp2 = await client.get("/api/v1/rentals/contracts", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 402
    assert "Subscription upgrade required" in resp2.json()["detail"]


def _get_platform_admin_token(user: User) -> str:
    return create_access_token({
        "sub": str(user.id),
        "tenant_id": None,
        "role": "admin",
        "is_platform_admin": True,
    })


@pytest.mark.asyncio
async def test_platform_admin_can_manage_tenant_modules(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """Verify platform admins can view and modify a tenant's active modules."""
    # Seed module registry
    m1 = Module(code="sales", name="Sales", is_core=False, is_active=True)
    m2 = Module(code="rental", name="Rental", is_core=False, is_active=True)
    db.add_all([m1, m2])
    await db.flush()

    plat_token = _get_platform_admin_token(admin_user)
    headers = {"Authorization": f"Bearer {plat_token}"}

    # 1. Retrieve modules list (should be empty initially)
    get_resp = await client.get(f"/api/v1/tenants/{tenant.id}/modules", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["modules"] == []

    # 2. Update modules list to include 'sales'
    post_resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/modules",
        headers=headers,
        json={"module_codes": ["sales"]}
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["modules"] == ["sales"]

    # 3. Retrieve modules list again (should show 'sales')
    get_resp2 = await client.get(f"/api/v1/tenants/{tenant.id}/modules", headers=headers)
    assert get_resp2.status_code == 200
    assert get_resp2.json()["modules"] == ["sales"]


@pytest.mark.asyncio
async def test_non_platform_admin_cannot_manage_tenant_modules(client: AsyncClient, tenant: Tenant, admin_user: User):
    """Ensure normal tenant users cannot manage subscription modules."""
    normal_token = _get_token(admin_user, tenant)
    headers = {"Authorization": f"Bearer {normal_token}"}

    get_resp = await client.get(f"/api/v1/tenants/{tenant.id}/modules", headers=headers)
    assert get_resp.status_code == 403 # Forbidden


@pytest.mark.asyncio
async def test_report_catalogue_subscription_filtering(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """Verify standard reports catalogue displays only reports matching active tenant modules."""
    # Register core modules
    m1 = Module(code="sales", name="Sales", is_core=False, is_active=True)
    m2 = Module(code="amc", name="AMC", is_core=False, is_active=True)
    db.add_all([m1, m2])
    await db.flush()

    # Active modules: only 'sales'
    tm = TenantModule(
        tenant_id=tenant.id,
        module_code="sales",
        status="active",
        starts_at=datetime.now(timezone.utc)
    )
    db.add(tm)
    await db.flush()

    token = _get_token(admin_user, tenant)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/reports/catalogue", headers=headers)
    assert resp.status_code == 200
    reports = resp.json()["reports"]
    
    # Extract keys
    keys = [r["key"] for r in reports]
    # Revenue by Customer (requires sales) should be present
    assert "revenue-by-customer" in keys
    # AMC renewal pipeline (requires amc) should not be present
    assert "amc-renewal-pipeline" not in keys


@pytest.mark.asyncio
async def test_standard_report_restricted_by_subscription(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """Verify requesting a standard report for a disabled module returns 402."""
    # Active modules: only 'sales'
    m1 = Module(code="sales", name="Sales", is_core=False, is_active=True)
    db.add(m1)
    tm = TenantModule(
        tenant_id=tenant.id,
        module_code="sales",
        status="active",
        starts_at=datetime.now(timezone.utc)
    )
    db.add(tm)
    await db.flush()

    token = _get_token(admin_user, tenant)
    headers = {"Authorization": f"Bearer {token}"}

    # Revenue by Customer (sales module) should be allowed (empty response or data)
    resp = await client.get("/api/v1/reports/revenue-by-customer", headers=headers)
    assert resp.status_code == 200

    # AMC renewal pipeline (amc module) should be blocked with 402
    resp2 = await client.get("/api/v1/reports/amc-renewal-pipeline", headers=headers)
    assert resp2.status_code == 402
    assert "Subscription upgrade required" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_dashboard_kpis_filtered_by_subscription(client: AsyncClient, tenant: Tenant, admin_user: User, db: AsyncSession):
    """Verify dashboard endpoint returns zeroed values for unsubscribed/disabled modules."""
    # Active modules: only 'sales'
    m1 = Module(code="sales", name="Sales", is_core=False, is_active=True)
    db.add(m1)
    tm = TenantModule(
        tenant_id=tenant.id,
        module_code="sales",
        status="active",
        starts_at=datetime.now(timezone.utc)
    )
    db.add(tm)
    await db.flush()

    token = _get_token(admin_user, tenant)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/reports/dashboard", headers=headers)
    assert resp.status_code == 200
    kpis = resp.json()
    
    # AMC/Service ticket metrics should be 0 because AMC is not in subscription
    assert kpis["open_tickets"] == 0
    assert kpis["sla_breached_tickets"] == 0
    assert kpis["active_amc_contracts"] == 0
