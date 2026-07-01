from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse, ContactCreate, ContactResponse,
)
from app.services import customer as customer_service

router = APIRouter()


@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await customer_service.list_customers(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customers:write")),
):
    return await customer_service.create_customer(db, current_user.tenant_id, payload)


@router.get("/sites")
async def list_all_sites(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """All sites across the tenant (for asset/ticket site pickers). Declared
    before /{customer_id} so the literal path wins over the UUID param."""
    from sqlalchemy import select
    from app.models.customer import CustomerSite
    rows = (await db.execute(
        select(CustomerSite).where(CustomerSite.tenant_id == current_user.tenant_id)
    )).scalars().all()
    return [{"id": str(s.id), "name": s.name, "customer_id": str(s.customer_id),
             "address": s.address} for s in rows]


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await customer_service.get_customer(db, current_user.tenant_id, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customers:write")),
):
    return await customer_service.update_customer(db, current_user.tenant_id, customer_id, payload)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customers:write")),
):
    await customer_service.delete_customer(db, current_user.tenant_id, customer_id)


@router.get("/{customer_id}/contacts", response_model=List[ContactResponse])
async def list_contacts(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await customer_service.list_contacts(db, current_user.tenant_id, customer_id)


@router.post("/{customer_id}/contacts", response_model=ContactResponse, status_code=201)
async def add_contact(
    customer_id: UUID,
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("customers:write")),
):
    return await customer_service.add_contact(db, current_user.tenant_id, customer_id, payload)


@router.get("/{customer_id}/history")
async def interaction_history(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await customer_service.interaction_history(db, current_user.tenant_id, customer_id)
