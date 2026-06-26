from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.services import company as company_service

router = APIRouter()

@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await company_service.list_companies(db, current_user.tenant_id, limit=100)

@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),  # Admin permission
):
    return await company_service.create_company(db, current_user.tenant_id, payload)

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await company_service.get_company(db, current_user.tenant_id, company_id)

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),
):
    return await company_service.update_company(db, current_user.tenant_id, company_id, payload)

@router.delete("/{company_id}", response_model=CompanyResponse)
async def delete_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),
):
    # Soft delete: mark active = False
    return await company_service.update_company(
        db, current_user.tenant_id, company_id, CompanyUpdate(is_active=False)
    )
