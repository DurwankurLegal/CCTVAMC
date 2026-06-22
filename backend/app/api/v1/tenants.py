from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_platform_admin
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services import tenant as tenant_service

router = APIRouter()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.list_tenants(db)


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    payload: TenantCreate, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.create_tenant(db, payload)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.get_tenant(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID, payload: TenantUpdate, db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    return await tenant_service.update_tenant(db, tenant_id, payload)
