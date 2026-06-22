from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.amc import AMCContractCreate, AMCContractUpdate, AMCContractResponse
from app.services import amc as amc_service

router = APIRouter()


@router.get("", response_model=List[AMCContractResponse])
async def list_amc(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await amc_service.list_amc(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=AMCContractResponse, status_code=201)
async def create_amc(
    payload: AMCContractCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await amc_service.create_amc(db, current_user.tenant_id, payload)


@router.get("/{amc_id}", response_model=AMCContractResponse)
async def get_amc(
    amc_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await amc_service.get_amc(db, current_user.tenant_id, amc_id)


@router.patch("/{amc_id}", response_model=AMCContractResponse)
async def update_amc(
    amc_id: UUID, payload: AMCContractUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    return await amc_service.update_amc(db, current_user.tenant_id, amc_id, payload)
