"""
Integration tests — Phase 2 tenant provisioning
=================================================
POST /tenants/provision creates tenant + first admin + workspace defaults and
returns one-time credentials; the admin must reset its temp password.
"""
import uuid

import pytest
from sqlalchemy import select, func
from app.models.notification import NotificationTemplate, NotificationChannel
from app.models.user import User
from app.services import notification_events as ev
from app.services.notification import NotificationService
from app.services.provisioning import seed_templates


def _provision_body(slug, *, admin=True):
    body = {"tenant": {"name": f"Co {slug}", "slug": slug, "plan": "starter"}}
    if admin:
        body |= {"admin_email": f"admin@{slug}.com", "admin_full_name": "First Admin"}
    return body


@pytest.mark.asyncio
async def test_provision_returns_admin_and_temp_password(client, platform_headers):
    r = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                          json=_provision_body("acme-sec"))
    assert r.status_code == 201
    body = r.json()
    assert body["tenant"]["slug"] == "acme-sec"
    assert body["first_admin"]["email"] == "admin@acme-sec.com"
    assert body["first_admin"]["must_change_password"] is True
    assert body["temp_password"]            # present and non-empty
    # Workspace defaults applied.
    assert body["tenant"]["settings"].get("currency") == "INR"
    assert body["tenant"]["branding"].get("primary_color")


@pytest.mark.asyncio
async def test_provisioned_admin_login_then_forced_reset(client, platform_headers):
    r = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                          json=_provision_body("reset-co"))
    temp = r.json()["temp_password"]

    # 1. Admin logs in with the temp password.
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@reset-co.com", "password": temp, "tenant_slug": "reset-co"})
    assert login.status_code == 200
    access = login.json()["access_token"]
    hdr = {"Authorization": f"Bearer {access}"}

    # 2. /auth/me flags the forced reset.
    me = await client.get("/api/v1/auth/me", headers=hdr)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    # 3. Change the password → flag clears.
    chg = await client.post("/api/v1/auth/change-password", headers=hdr,
                            json={"current_password": temp, "new_password": "BrandNew@123"})
    assert chg.status_code == 200
    me2 = await client.get("/api/v1/auth/me", headers=hdr)
    assert me2.json()["must_change_password"] is False

    # 4. Old temp password no longer works; the new one does.
    old = await client.post("/api/v1/auth/login", json={
        "email": "admin@reset-co.com", "password": temp, "tenant_slug": "reset-co"})
    assert old.status_code == 401
    new = await client.post("/api/v1/auth/login", json={
        "email": "admin@reset-co.com", "password": "BrandNew@123", "tenant_slug": "reset-co"})
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_rejected(client, platform_headers):
    r = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                          json=_provision_body("wrongpw-co"))
    temp = r.json()["temp_password"]
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@wrongpw-co.com", "password": temp, "tenant_slug": "wrongpw-co"})
    hdr = {"Authorization": f"Bearer {login.json()['access_token']}"}
    chg = await client.post("/api/v1/auth/change-password", headers=hdr,
                            json={"current_password": "not-it", "new_password": "BrandNew@123"})
    assert chg.status_code == 401


@pytest.mark.asyncio
async def test_provision_seeds_notification_templates(client, db, platform_headers):
    r = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                          json=_provision_body("tmpl-co"))
    tenant_id = uuid.UUID(r.json()["tenant"]["id"])

    count = (await db.execute(
        select(func.count()).select_from(NotificationTemplate)
        .where(NotificationTemplate.tenant_id == tenant_id))).scalar()
    assert count and count > 0

    # The seeded template is actually used (IN_APP avoids Celery dispatch).
    log = await NotificationService(db, tenant_id).send(
        ev.TICKET_ASSIGNED,
        recipient="tech@tmpl-co.com",
        context={"ticket_number": "TKT-1", "priority": "high"},
        channel=NotificationChannel.IN_APP.value,
    )
    assert log.subject == "New ticket assigned: TKT-1"   # not the generic fallback


@pytest.mark.asyncio
async def test_seed_templates_is_idempotent(client, db, platform_headers):
    r = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                          json=_provision_body("idem-co"))
    tenant_id = uuid.UUID(r.json()["tenant"]["id"])
    # Re-seeding inserts nothing more.
    assert await seed_templates(db, tenant_id) == 0


@pytest.mark.asyncio
async def test_provision_duplicate_slug_conflicts(client, db, platform_headers):
    r1 = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                           json=_provision_body("dup-co"))
    assert r1.status_code == 201
    # Re-provisioning the same slug is rejected (slug uniqueness, via create_tenant).
    r2 = await client.post("/api/v1/tenants/provision", headers=platform_headers,
                           json=_provision_body("dup-co"))
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_plain_create_still_works_without_admin(client, db, platform_headers):
    """Back-compat: the original POST /tenants creates no admin."""
    r = await client.post("/api/v1/tenants", headers=platform_headers,
                          json={"name": "Plain Co", "slug": "plain-co", "plan": "starter"})
    assert r.status_code == 201
    tenant_id = uuid.UUID(r.json()["id"])
    admins = (await db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id))).scalar()
    assert admins == 0
