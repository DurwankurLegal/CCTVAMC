from typing import List
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.service_ticket import ServiceTicketCreate, ServiceTicketUpdate, ServiceTicketResponse
from app.services import service_ticket as ticket_service

router = APIRouter()


class CommentCreate(BaseModel):
    body: str


@router.get("", response_model=List[ServiceTicketResponse])
async def list_tickets(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ticket_service.list_tickets(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=ServiceTicketResponse, status_code=201)
async def create_ticket(
    payload: ServiceTicketCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ticket_service.create_ticket(db, current_user.tenant_id, payload)


@router.get("/{ticket_id}", response_model=ServiceTicketResponse)
async def get_ticket(
    ticket_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ticket_service.get_ticket(db, current_user.tenant_id, ticket_id)


@router.patch("/{ticket_id}", response_model=ServiceTicketResponse)
async def update_ticket(
    ticket_id: UUID, payload: ServiceTicketUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("service_tickets:write")),
):
    return await ticket_service.update_ticket(db, current_user.tenant_id, ticket_id, payload)


@router.get("/{ticket_id}/comments")
async def list_comments(
    ticket_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = await ticket_service.list_comments(db, current_user.tenant_id, ticket_id)
    return [{"id": str(c.id), "body": c.body, "author_id": str(c.author_id) if c.author_id else None,
             "created_at": c.created_at.isoformat()} for c in rows]


@router.post("/{ticket_id}/comments", status_code=201)
async def add_comment(
    ticket_id: UUID, payload: CommentCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("service_tickets:write")),
):
    c = await ticket_service.add_comment(db, current_user.tenant_id, ticket_id, payload.body, current_user.user_id)
    return {"id": str(c.id), "body": c.body}
