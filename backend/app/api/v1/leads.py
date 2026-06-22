from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.schemas.customer import CustomerResponse
from app.services import lead as lead_service

router = APIRouter()


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await lead_service.list_leads(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await lead_service.create_lead(db, current_user.tenant_id, payload)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await lead_service.get_lead(db, current_user.tenant_id, lead_id)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID, payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await lead_service.update_lead(db, current_user.tenant_id, lead_id, payload)


@router.post("/{lead_id}/convert", response_model=CustomerResponse)
async def convert_lead(
    lead_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    """One-click lead → customer conversion."""
    return await lead_service.convert_to_customer(db, current_user.tenant_id, lead_id)
