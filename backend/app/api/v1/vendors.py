from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from app.services import vendor as vendor_service

router = APIRouter()


@router.get("", response_model=List[VendorResponse])
async def list_vendors(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await vendor_service.list_vendors(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(
    payload: VendorCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await vendor_service.create_vendor(db, current_user.tenant_id, payload)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await vendor_service.get_vendor(db, current_user.tenant_id, vendor_id)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID, payload: VendorUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await vendor_service.update_vendor(db, current_user.tenant_id, vendor_id, payload)
