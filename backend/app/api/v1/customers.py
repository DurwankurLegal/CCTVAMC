from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
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
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await customer_service.create_customer(db, current_user.tenant_id, payload)


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
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await customer_service.update_customer(db, current_user.tenant_id, customer_id, payload)
