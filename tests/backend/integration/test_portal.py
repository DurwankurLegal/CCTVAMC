"""
Integration tests — Customer Self-Service Portal API
=======================================================
Covers: portal login (success + bad creds), token-scoped access, dashboard,
        ticket raise/list/detail/comment, and cross-scope isolation
        (staff token rejected on portal; portal token rejected on staff APIs).
"""
import uuid
import pytest
import pytest_asyncio

from conftest import TENANT_ID, CUSTOMER_ID


BASE = "/api/v1/portal"
PORTAL_EMAIL = "owner@customer.com"
PORTAL_PASSWORD = "Portal@123"


@pytest_asyncio.fixture()
async def portal_user(db, customer):
    from app.core.security import hash_password
    from app.models.customer_portal_user import CustomerPortalUser
    u = CustomerPortalUser(
        id=uuid.uuid4(), tenant_id=TENANT_ID, customer_id=CUSTOMER_ID,
        email=PORTAL_EMAIL, full_name="Customer Owner",
        hashed_password=hash_password(PORTAL_PASSWORD), is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _portal_token(client, portal_user) -> str:
    r = await client.post(f"{BASE}/login", json={
        "email": PORTAL_EMAIL, "password": PORTAL_PASSWORD, "tenant_slug": "test-corp",
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portal_login_success(client, portal_user):
    r = await client.post(f"{BASE}/login", json={
        "email": PORTAL_EMAIL, "password": PORTAL_PASSWORD, "tenant_slug": "test-corp",
    })
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_portal_login_bad_password(client, portal_user):
    r = await client.post(f"{BASE}/login", json={
        "email": PORTAL_EMAIL, "password": "wrong", "tenant_slug": "test-corp",
    })
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_portal_me(client, portal_user):
    tok = await _portal_token(client, portal_user)
    r = await client.get(f"{BASE}/me", headers=_h(tok))
    assert r.status_code == 200
    assert r.json()["email"] == PORTAL_EMAIL


@pytest.mark.asyncio
async def test_portal_dashboard(client, portal_user):
    tok = await _portal_token(client, portal_user)
    r = await client.get(f"{BASE}/dashboard", headers=_h(tok))
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_portal_tickets_empty(client, portal_user):
    tok = await _portal_token(client, portal_user)
    r = await client.get(f"{BASE}/tickets", headers=_h(tok))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_portal_raise_and_list_ticket(client, portal_user):
    tok = await _portal_token(client, portal_user)
    cr = await client.post(f"{BASE}/tickets",
                           json={"complaint": "Camera 3 offline", "priority": "high"},
                           headers=_h(tok))
    assert cr.status_code == 201, cr.text
    tid = cr.json()["id"]
    lr = await client.get(f"{BASE}/tickets", headers=_h(tok))
    assert tid in [t["id"] for t in lr.json()]


@pytest.mark.asyncio
async def test_portal_ticket_detail_and_comment(client, portal_user):
    tok = await _portal_token(client, portal_user)
    cr = await client.post(f"{BASE}/tickets",
                           json={"complaint": "NVR not booting"},
                           headers=_h(tok))
    tid = cr.json()["id"]
    dr = await client.get(f"{BASE}/tickets/{tid}", headers=_h(tok))
    assert dr.status_code == 200
    cm = await client.post(f"{BASE}/tickets/{tid}/comments",
                           json={"body": "Any update?"}, headers=_h(tok))
    assert cm.status_code == 201, cm.text


# ── Cross-scope isolation ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_token_rejected_on_portal(client, auth_headers):
    """A staff JWT has no portal scope and must be rejected by portal routes."""
    r = await client.get(f"{BASE}/me", headers=auth_headers)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_portal_token_rejected_on_staff_api(client, portal_user):
    """A portal-scoped JWT must never reach staff/back-office APIs."""
    tok = await _portal_token(client, portal_user)
    r = await client.get("/api/v1/customers", headers=_h(tok))
    assert r.status_code in (401, 403)
