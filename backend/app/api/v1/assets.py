from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse
from app.services import asset as asset_service

router = APIRouter()


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await asset_service.list_assets(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    payload: AssetCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("assets:write")),
):
    return await asset_service.create_asset(db, current_user.tenant_id, payload)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await asset_service.get_asset(db, current_user.tenant_id, asset_id)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID, payload: AssetUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("assets:write")),
):
    return await asset_service.update_asset(db, current_user.tenant_id, asset_id, payload)
