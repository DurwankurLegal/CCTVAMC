from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.service_ticket import ServiceTicket, TicketStatus
from app.repositories.base import TenantRepository
from app.schemas.service_ticket import ServiceTicketCreate, ServiceTicketUpdate
from app.services.sequences import next_number

# SLA hours by priority
SLA_HOURS = {"critical": 4, "high": 8, "medium": 24, "low": 48}


class ServiceTicketRepository(TenantRepository[ServiceTicket]):
    model = ServiceTicket


async def add_comment(db: AsyncSession, tenant_id: UUID, ticket_id: UUID, body: str, author_id):
    from app.models.ticket_comment import TicketComment
    from sqlalchemy import select
    if not await ServiceTicketRepository(db, tenant_id).get(ticket_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    class _Repo(TenantRepository[TicketComment]):
        model = TicketComment
    comment = TicketComment(ticket_id=ticket_id, body=body, author_id=author_id)
    return await _Repo(db, tenant_id).create(comment)


async def list_comments(db: AsyncSession, tenant_id: UUID, ticket_id: UUID):
    from app.models.ticket_comment import TicketComment
    from sqlalchemy import select
    rows = await db.execute(
        select(TicketComment).where(
            TicketComment.tenant_id == tenant_id,
            TicketComment.ticket_id == ticket_id,
        ).order_by(TicketComment.created_at)
    )
    return list(rows.scalars().all())


async def list_tickets(db: AsyncSession, tenant_id: UUID, offset: int, limit: int):
    repo = ServiceTicketRepository(db, tenant_id)
    return await repo.list(offset=offset, limit=limit)


async def get_ticket(db: AsyncSession, tenant_id: UUID, ticket_id: UUID) -> ServiceTicket:
    repo = ServiceTicketRepository(db, tenant_id)
    obj = await repo.get(ticket_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return obj


async def create_ticket(db: AsyncSession, tenant_id: UUID, payload: ServiceTicketCreate) -> ServiceTicket:
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, tenant_id, payload.company_id)
    repo = ServiceTicketRepository(db, tenant_id)
    sla_hours = SLA_HOURS.get(payload.priority.value, 24)
    
    data = payload.model_dump()
    data["company_id"] = comp_id
    
    obj = ServiceTicket(
        **data,
        ticket_number=await next_number(db, tenant_id, "ticket", "TKT"),
        sla_due_at=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
    )
    return await repo.create(obj)


async def update_ticket(db: AsyncSession, tenant_id: UUID, ticket_id: UUID, payload: ServiceTicketUpdate) -> ServiceTicket:
    repo = ServiceTicketRepository(db, tenant_id)
    obj = await repo.get(ticket_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    previous_assignee = obj.assigned_to
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(obj, key, val)
    if payload.status == TicketStatus.RESOLVED:
        obj.resolved_at = datetime.now(timezone.utc)
    elif payload.status == TicketStatus.CLOSED:
        obj.closed_at = datetime.now(timezone.utc)
    saved = await repo.save(obj)

    # Notify the technician when a ticket is (re)assigned.
    if obj.assigned_to and obj.assigned_to != previous_assignee:
        from app.services.notification import NotificationService
        from app.services.notification_events import TICKET_ASSIGNED
        from app.models.notification import NotificationChannel
        await NotificationService(db, tenant_id).send(
            TICKET_ASSIGNED,
            recipient=str(obj.assigned_to),
            context={"ticket_number": obj.ticket_number, "priority": obj.priority},
            channel=NotificationChannel.IN_APP,
            recipient_user_id=obj.assigned_to,
        )
    return saved
