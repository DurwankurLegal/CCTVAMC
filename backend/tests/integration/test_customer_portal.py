"""Customer self-service portal (Step 3): customer-scoped isolation and the
raise-ticket flow. Critical security assertions:
  - portal token cannot reach staff APIs (and vice versa)
  - customer A cannot see customer B's data within the same tenant
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.customer_portal_user import CustomerPortalUser
from app.models.service_ticket import ServiceTicket, TicketStatus, TicketPriority
from app.core.security import hash_password


async def _make_customer(db: AsyncSession, tenant_id, name) -> Customer:
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, name=name, category="commercial")
    db.add(c)
    await db.flush()
    return c


async def _make_portal_user(db: AsyncSession, tenant_id, customer_id, email) -> None:
    db.add(CustomerPortalUser(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id,
        email=email, full_name="Portal User", hashed_password=hash_password("password123")))
    await db.flush()


async def _portal_login(client: AsyncClient, email, tenant_slug) -> str:
    resp = await client.post("/api/v1/portal/login",
                             json={"email": email, "password": "password123", "tenant_slug": tenant_slug})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.mark.asyncio
async def test_portal_login_and_raise_ticket(client: AsyncClient, db: AsyncSession, tenant):
    cust = await _make_customer(db, tenant.id, "Portal Customer A")
    await _make_portal_user(db, tenant.id, cust.id, "a@portal.test")
    token = await _portal_login(client, "a@portal.test", tenant.slug)

    # me + empty ticket list
    me = await client.get("/api/v1/portal/me", headers=_auth(token))
    assert me.status_code == 200 and me.json()["customer_id"] == str(cust.id)
    assert (await client.get("/api/v1/portal/tickets", headers=_auth(token))).json() == []

    # raise a ticket
    created = await client.post("/api/v1/portal/tickets", headers=_auth(token),
                                json={"complaint": "Camera offline", "priority": "high"})
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    assert created.json()["ticket_number"]

    # appears in the customer's list and detail
    listed = await client.get("/api/v1/portal/tickets", headers=_auth(token))
    assert tid in [t["id"] for t in listed.json()]
    detail = await client.get(f"/api/v1/portal/tickets/{tid}", headers=_auth(token))
    assert detail.status_code == 200 and detail.json()["complaint"] == "Camera offline"

    # comment flow
    cmt = await client.post(f"/api/v1/portal/tickets/{tid}/comments", headers=_auth(token),
                            json={"body": "Any update?"})
    assert cmt.status_code == 201
    assert any(c["body"] == "Any update?"
               for c in (await client.get(f"/api/v1/portal/tickets/{tid}", headers=_auth(token))).json()["comments"])


@pytest.mark.asyncio
async def test_customer_cannot_see_other_customer_tickets(client: AsyncClient, db: AsyncSession, tenant):
    cust_a = await _make_customer(db, tenant.id, "Cust A")
    cust_b = await _make_customer(db, tenant.id, "Cust B")
    await _make_portal_user(db, tenant.id, cust_a.id, "a2@portal.test")
    await _make_portal_user(db, tenant.id, cust_b.id, "b2@portal.test")

    # B has a ticket
    b_ticket = ServiceTicket(id=uuid.uuid4(), tenant_id=tenant.id, customer_id=cust_b.id,
                             ticket_number="TKT-B-1", status=TicketStatus.OPEN,
                             priority=TicketPriority.LOW, complaint="B private issue")
    db.add(b_ticket)
    await db.flush()

    token_a = await _portal_login(client, "a2@portal.test", tenant.slug)
    # A's list must not include B's ticket
    listed = await client.get("/api/v1/portal/tickets", headers=_auth(token_a))
    assert str(b_ticket.id) not in [t["id"] for t in listed.json()]
    # A cannot fetch B's ticket directly
    direct = await client.get(f"/api/v1/portal/tickets/{b_ticket.id}", headers=_auth(token_a))
    assert direct.status_code == 404


@pytest.mark.asyncio
async def test_portal_token_rejected_by_staff_api(client: AsyncClient, db: AsyncSession, tenant):
    cust = await _make_customer(db, tenant.id, "Cust X")
    await _make_portal_user(db, tenant.id, cust.id, "x@portal.test")
    token = await _portal_login(client, "x@portal.test", tenant.slug)
    # Staff endpoints must reject a portal-scoped token.
    resp = await client.get("/api/v1/customers", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_token_rejected_by_portal_api(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/portal/me", headers=_auth(admin_token))
    assert resp.status_code == 401
