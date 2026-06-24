"""
End-to-end test — Phase 2 onboarding journey (API-level, full request cycle)
============================================================================
Platform admin provisions a company → the new admin logs in with the temp
password → forced reset → logs in fresh → reaches an authenticated endpoint.
"""
import pytest


@pytest.mark.asyncio
async def test_e2e_onboard_to_first_use(client, platform_headers):
    slug = "journey-co"

    # 1. Platform admin onboards the company in one call.
    prov = await client.post("/api/v1/tenants/provision", headers=platform_headers, json={
        "tenant": {"name": "Journey Co", "slug": slug, "plan": "growth"},
        "admin_email": f"admin@{slug}.com", "admin_full_name": "Owner",
    })
    assert prov.status_code == 201
    temp = prov.json()["temp_password"]
    assert prov.json()["first_admin"]["must_change_password"] is True

    # 2. New admin logs in with the temp password.
    login = await client.post("/api/v1/auth/login", json={
        "email": f"admin@{slug}.com", "password": temp, "tenant_slug": slug})
    assert login.status_code == 200
    hdr = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 3. Forced reset.
    chg = await client.post("/api/v1/auth/change-password", headers=hdr,
                            json={"current_password": temp, "new_password": "Owner@2026!"})
    assert chg.status_code == 200

    # 4. Fresh login with the new password.
    relogin = await client.post("/api/v1/auth/login", json={
        "email": f"admin@{slug}.com", "password": "Owner@2026!", "tenant_slug": slug})
    assert relogin.status_code == 200
    hdr2 = {"Authorization": f"Bearer {relogin.json()['access_token']}"}

    # 5. The admin can use the app (tenant-scoped endpoint returns its own data).
    customers = await client.get("/api/v1/customers", headers=hdr2)
    assert customers.status_code == 200
    assert isinstance(customers.json(), list)


@pytest.mark.asyncio
async def test_e2e_admin_supplied_password_skips_forced_reset(client, platform_headers):
    """When the platform admin sets the password, no forced reset is required."""
    slug = "preset-co"
    prov = await client.post("/api/v1/tenants/provision", headers=platform_headers, json={
        "tenant": {"name": "Preset Co", "slug": slug, "plan": "starter"},
        "admin_email": f"admin@{slug}.com", "admin_full_name": "Owner",
        "admin_password": "Preset@123",
    })
    assert prov.status_code == 201
    assert prov.json()["first_admin"]["must_change_password"] is False
    # No temp password is generated when one was supplied.
    assert prov.json()["temp_password"] == "Preset@123" or prov.json()["temp_password"] is None

    login = await client.post("/api/v1/auth/login", json={
        "email": f"admin@{slug}.com", "password": "Preset@123", "tenant_slug": slug})
    assert login.status_code == 200
    me = await client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_e2e_provisioned_tenants_are_isolated(client, platform_headers):
    """Two onboarded companies cannot see each other's data — provisioning must
    produce properly tenant-scoped admins."""
    async def onboard(slug):
        r = await client.post("/api/v1/tenants/provision", headers=platform_headers, json={
            "tenant": {"name": slug, "slug": slug, "plan": "growth"},
            "admin_email": f"admin@{slug}.com", "admin_full_name": "A",
            "admin_password": "Iso@12345",
        })
        assert r.status_code == 201
        login = await client.post("/api/v1/auth/login", json={
            "email": f"admin@{slug}.com", "password": "Iso@12345", "tenant_slug": slug})
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    hdr_a = await onboard("iso-a")
    hdr_b = await onboard("iso-b")

    # Tenant A's admin creates a customer.
    created = await client.post("/api/v1/customers", headers=hdr_a,
                                json={"name": "A-Only Customer", "category": "commercial"})
    assert created.status_code == 201

    # A sees it; B does not.
    a_names = [c["name"] for c in (await client.get("/api/v1/customers", headers=hdr_a)).json()]
    b_names = [c["name"] for c in (await client.get("/api/v1/customers", headers=hdr_b)).json()]
    assert "A-Only Customer" in a_names
    assert "A-Only Customer" not in b_names
