"""Customer self-service portal (SRS 4.2).

Every read/write here is scoped by BOTH ``tenant_id`` (RLS + filter) and the
portal user's ``customer_id`` (application filter), so customer A can never see
customer B's data even within the same tenant.
"""
from uuid import UUID
from typing import Optional
from datetime import date
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.customer_portal_user import CustomerPortalUser
from app.models.tenant import Tenant
from app.models.customer import Customer, CustomerSite
from app.models.asset import CCTVAsset
from app.models.amc import AMCContract
from app.models.invoice import Invoice
from app.models.service_ticket import ServiceTicket, TicketStatus
from app.models.auth_session import AuthSession
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, decode_token,
)
from app.schemas.service_ticket import ServiceTicketCreate
from app.services import service_ticket as ticket_service


async def _set_rls(db: AsyncSession, tenant_id: UUID) -> None:
    conn = await db.connection()
    if conn.dialect.name == "postgresql":
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})


def _portal_claims(u: CustomerPortalUser) -> dict:
    return {
        "sub": str(u.id),
        "tenant_id": str(u.tenant_id),
        "customer_id": str(u.customer_id),
        "scope": "portal",
    }


async def _issue_tokens(db: AsyncSession, u: CustomerPortalUser) -> dict:
    data = _portal_claims(u)
    access = create_access_token(data)
    refresh, jti, expires_at = create_refresh_token(data)
    db.add(AuthSession(user_id=u.id, tenant_id=u.tenant_id, jti=jti, expires_at=expires_at))
    await db.flush()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def login(db: AsyncSession, email: str, password: str, tenant_slug: str) -> dict:
    tid = (await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))).scalar_one_or_none()
    if not tid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    await _set_rls(db, tid)
    u = (await db.execute(select(CustomerPortalUser).where(
        CustomerPortalUser.tenant_id == tid,
        CustomerPortalUser.email == email,
        CustomerPortalUser.is_active == True,
    ))).scalar_one_or_none()
    if not u or not verify_password(password, u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return await _issue_tokens(db, u)


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    claims = decode_token(refresh_token)
    if not claims or claims.get("type") != "refresh" or claims.get("scope") != "portal" or not claims.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    session = (await db.execute(
        select(AuthSession).where(AuthSession.jti == claims["jti"]))).scalar_one_or_none()
    if not session or session.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    await _set_rls(db, UUID(claims["tenant_id"]))
    u = (await db.execute(select(CustomerPortalUser).where(
        CustomerPortalUser.id == UUID(claims["sub"]),
        CustomerPortalUser.is_active == True,
    ))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    session.revoked = True
    await db.flush()
    return await _issue_tokens(db, u)


async def me(db: AsyncSession, portal) -> dict:
    await _set_rls(db, portal.tenant_id)
    u = (await db.execute(select(CustomerPortalUser).where(
        CustomerPortalUser.id == portal.user_id))).scalar_one_or_none()
    cust = (await db.execute(select(Customer).where(
        Customer.id == portal.customer_id, Customer.tenant_id == portal.tenant_id))).scalar_one_or_none()
    if not u or not cust:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {
        "id": str(u.id), "email": u.email, "full_name": u.full_name,
        "customer_id": str(cust.id), "customer_name": cust.name,
    }


# ── Customer-scoped reads ────────────────────────────────────────────────────

async def list_sites(db: AsyncSession, portal):
    await _set_rls(db, portal.tenant_id)
    rows = (await db.execute(select(CustomerSite).where(
        CustomerSite.tenant_id == portal.tenant_id,
        CustomerSite.customer_id == portal.customer_id))).scalars().all()
    return [{"id": str(s.id), "name": s.name, "address": s.address} for s in rows]


async def list_assets(db: AsyncSession, portal):
    """Assets at any of the customer's sites (assets link to customer via site)."""
    await _set_rls(db, portal.tenant_id)
    rows = (await db.execute(
        select(CCTVAsset)
        .join(CustomerSite, CCTVAsset.site_id == CustomerSite.id)
        .where(CustomerSite.tenant_id == portal.tenant_id,
               CustomerSite.customer_id == portal.customer_id))).scalars().all()
    return [{"id": str(a.id), "serial_number": a.serial_number, "model": a.model,
             "status": a.status, "site_id": str(a.site_id),
             "warranty_expiry": a.warranty_expiry.isoformat() if a.warranty_expiry else None}
            for a in rows]


async def list_amc(db: AsyncSession, portal):
    await _set_rls(db, portal.tenant_id)
    rows = (await db.execute(select(AMCContract).where(
        AMCContract.tenant_id == portal.tenant_id,
        AMCContract.customer_id == portal.customer_id))).scalars().all()
    return [{"id": str(c.id), "contract_number": c.contract_number, "status": c.status,
             "start_date": c.start_date.isoformat(), "end_date": c.end_date.isoformat(),
             "annual_amount": float(c.annual_amount)} for c in rows]


async def list_invoices(db: AsyncSession, portal):
    await _set_rls(db, portal.tenant_id)
    rows = (await db.execute(select(Invoice).where(
        Invoice.tenant_id == portal.tenant_id,
        Invoice.customer_id == portal.customer_id))).scalars().all()
    return [{"id": str(i.id), "invoice_number": i.invoice_number, "status": i.status,
             "invoice_date": i.invoice_date.isoformat() if i.invoice_date else None,
             "due_date": i.due_date.isoformat() if i.due_date else None,
             "total_amount": float(i.total_amount), "amount_paid": float(i.amount_paid)}
            for i in rows]


def _ticket_dict(t: ServiceTicket) -> dict:
    return {"id": str(t.id), "ticket_number": t.ticket_number, "status": t.status,
            "priority": t.priority, "complaint": t.complaint,
            "resolution_notes": t.resolution_notes,
            "site_id": str(t.site_id) if t.site_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None}


async def list_tickets(db: AsyncSession, portal):
    await _set_rls(db, portal.tenant_id)
    rows = (await db.execute(select(ServiceTicket).where(
        ServiceTicket.tenant_id == portal.tenant_id,
        ServiceTicket.customer_id == portal.customer_id,
    ).order_by(ServiceTicket.created_at.desc()))).scalars().all()
    return [_ticket_dict(t) for t in rows]


async def _owned_ticket(db: AsyncSession, portal, ticket_id: UUID) -> ServiceTicket:
    await _set_rls(db, portal.tenant_id)
    t = (await db.execute(select(ServiceTicket).where(
        ServiceTicket.id == ticket_id,
        ServiceTicket.tenant_id == portal.tenant_id,
        ServiceTicket.customer_id == portal.customer_id,
    ))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return t


async def get_ticket(db: AsyncSession, portal, ticket_id: UUID) -> dict:
    t = await _owned_ticket(db, portal, ticket_id)
    comments = await ticket_service.list_comments(db, portal.tenant_id, ticket_id)
    out = _ticket_dict(t)
    out["comments"] = [{"id": str(c.id), "body": c.body,
                        "created_at": c.created_at.isoformat() if c.created_at else None}
                       for c in comments]
    return out


async def create_ticket(db: AsyncSession, portal, priority: str, complaint: str,
                        site_id: Optional[UUID] = None) -> dict:
    await _set_rls(db, portal.tenant_id)
    # A supplied site must belong to this customer.
    if site_id:
        owns = (await db.execute(select(func.count()).where(
            CustomerSite.id == site_id, CustomerSite.tenant_id == portal.tenant_id,
            CustomerSite.customer_id == portal.customer_id))).scalar() or 0
        if not owns:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid site")

    payload = ServiceTicketCreate(
        customer_id=portal.customer_id, site_id=site_id, priority=priority, complaint=complaint)
    # Reuse the staff service: goes through TenantRepository (audit + RLS) and
    # sets SLA/ticket number. actor is the portal user (set on the request ctx).
    ticket = await ticket_service.create_ticket(db, portal.tenant_id, payload)

    # Notify tenant staff that a customer raised a ticket (in-app).
    from app.services.notification import NotificationService
    from app.services.notification_events import CUSTOMER_TICKET_CREATED
    from app.models.notification import NotificationChannel
    await NotificationService(db, portal.tenant_id).send(
        CUSTOMER_TICKET_CREATED,
        recipient="staff",
        context={"ticket_number": ticket.ticket_number, "priority": ticket.priority,
                 "complaint": ticket.complaint},
        channel=NotificationChannel.IN_APP,
    )
    return _ticket_dict(ticket)


async def add_comment(db: AsyncSession, portal, ticket_id: UUID, body: str) -> dict:
    await _owned_ticket(db, portal, ticket_id)
    comment = await ticket_service.add_comment(db, portal.tenant_id, ticket_id, body, portal.user_id)
    # Notify staff of the customer reply.
    from app.services.notification import NotificationService
    from app.services.notification_events import CUSTOMER_TICKET_COMMENT
    from app.models.notification import NotificationChannel
    await NotificationService(db, portal.tenant_id).send(
        CUSTOMER_TICKET_COMMENT, recipient="staff",
        context={"ticket_id": str(ticket_id)}, channel=NotificationChannel.IN_APP)
    return {"id": str(comment.id), "body": comment.body}


async def dashboard(db: AsyncSession, portal) -> dict:
    await _set_rls(db, portal.tenant_id)
    base = lambda model: select(func.count()).where(
        model.tenant_id == portal.tenant_id, model.customer_id == portal.customer_id)
    open_tickets = (await db.execute(base(ServiceTicket).where(
        ServiceTicket.status.in_([TicketStatus.OPEN.value, TicketStatus.ASSIGNED.value,
                                  TicketStatus.IN_PROGRESS.value])))).scalar() or 0
    total_tickets = (await db.execute(base(ServiceTicket))).scalar() or 0
    active_amc = (await db.execute(base(AMCContract).where(
        AMCContract.status == "active"))).scalar() or 0
    return {
        "open_tickets": open_tickets,
        "total_tickets": total_tickets,
        "active_amc_contracts": active_amc,
    }
