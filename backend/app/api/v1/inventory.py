from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse, StockAdjustment
from app.services import inventory as inv_service

router = APIRouter()


@router.get("", response_model=List[InventoryItemResponse])
async def list_items(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await inv_service.list_items(db, current_user.tenant_id, offset, limit)


@router.get("/low-stock", response_model=List[InventoryItemResponse])
async def low_stock_alert(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await inv_service.list_low_stock(db, current_user.tenant_id)


@router.post("", response_model=InventoryItemResponse, status_code=201)
async def create_item(
    payload: InventoryItemCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    return await inv_service.create_item(db, current_user.tenant_id, payload)


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def get_item(
    item_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await inv_service.get_item(db, current_user.tenant_id, item_id)


@router.patch("/{item_id}", response_model=InventoryItemResponse)
async def update_item(
    item_id: UUID, payload: InventoryItemUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    return await inv_service.update_item(db, current_user.tenant_id, item_id, payload)


@router.post("/adjust", response_model=InventoryItemResponse)
async def adjust_stock(
    payload: StockAdjustment, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("inventory:write")),
):
    return await inv_service.adjust_stock(db, current_user.tenant_id, payload)
