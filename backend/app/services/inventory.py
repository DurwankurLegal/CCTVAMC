from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.inventory import InventoryItem, InventoryMovement
from app.repositories.base import TenantRepository
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, StockAdjustment
from app.services.crud_base import make_crud


class ItemRepository(TenantRepository[InventoryItem]):
    model = InventoryItem


class MovementRepository(TenantRepository[InventoryMovement]):
    model = InventoryMovement


list_items, get_item_raw, create_item_raw, update_item = make_crud(ItemRepository, InventoryItem)


async def create_item(db, tenant_id, payload: InventoryItemCreate):
    return await create_item_raw(db, tenant_id, payload)


async def get_item(db, tenant_id, item_id):
    obj = await ItemRepository(db, tenant_id).get(item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return obj


async def adjust_stock(db: AsyncSession, tenant_id: UUID, payload: StockAdjustment) -> InventoryItem:
    item_repo = ItemRepository(db, tenant_id)
    item = await item_repo.get(payload.item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.current_stock += payload.quantity
    if item.current_stock < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    await item_repo.save(item)

    movement = InventoryMovement(
        item_id=payload.item_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
    )
    await MovementRepository(db, tenant_id).create(movement)
    return item


async def list_low_stock(db: AsyncSession, tenant_id: UUID):
    from sqlalchemy import select
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active == True,
            InventoryItem.current_stock <= InventoryItem.reorder_level,
        )
    )
    return list(result.scalars().all())
