from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.service_ticket import ServiceTicketCreate, ServiceTicketUpdate, ServiceTicketResponse
from app.services import service_ticket as ticket_service

router = APIRouter()


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
    current_user: CurrentUser = Depends(require_roles("admin", "manager", "technician")),
):
    return await ticket_service.update_ticket(db, current_user.tenant_id, ticket_id, payload)
