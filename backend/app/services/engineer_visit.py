from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.engineer_visit import EngineerVisit
from app.models.inventory import InventoryItem, InventoryMovement, MovementType
from app.repositories.base import TenantRepository
from app.schemas.engineer_visit import EngineerVisitCreate, CheckinRequest, CheckoutRequest


class VisitRepository(TenantRepository[EngineerVisit]):
    model = EngineerVisit


class ItemRepository(TenantRepository[InventoryItem]):
    model = InventoryItem


class MovementRepository(TenantRepository[InventoryMovement]):
    model = InventoryMovement


async def list_visits(db, tenant_id, offset=0, limit=50):
    return await VisitRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_visit(db, tenant_id, visit_id):
    obj = await VisitRepository(db, tenant_id).get(visit_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return obj


async def create_visit(db: AsyncSession, tenant_id: UUID, technician_id: UUID,
                       payload: EngineerVisitCreate) -> EngineerVisit:
    visit = EngineerVisit(
        ticket_id=payload.ticket_id,
        amc_contract_id=payload.amc_contract_id,
        technician_id=technician_id,
        visit_type=payload.visit_type,
    )
    return await VisitRepository(db, tenant_id).create(visit)


async def checkin(db: AsyncSession, tenant_id: UUID, visit_id: UUID,
                  payload: CheckinRequest) -> EngineerVisit:
    repo = VisitRepository(db, tenant_id)
    visit = await repo.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.checkin_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in")
    visit.checkin_at = datetime.now(timezone.utc)
    visit.checkin_lat = payload.lat
    visit.checkin_lng = payload.lng
    return await repo.save(visit)


async def checkout(db: AsyncSession, tenant_id: UUID, visit_id: UUID,
                   payload: CheckoutRequest) -> EngineerVisit:
    repo = VisitRepository(db, tenant_id)
    item_repo = ItemRepository(db, tenant_id)
    movement_repo = MovementRepository(db, tenant_id)

    visit = await repo.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.checkout_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked out")
    if not visit.checkin_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must check in first")

    visit.checkout_at = datetime.now(timezone.utc)
    visit.checkout_lat = payload.lat
    visit.checkout_lng = payload.lng
    visit.work_performed = payload.work_performed
    visit.parts_used = [p.model_dump() for p in payload.parts_used]
    visit.customer_feedback = payload.customer_feedback

    # Deduct inventory for each part consumed
    for part in payload.parts_used:
        item = await item_repo.get(part.item_id)
        if item:
            item.current_stock = max(0, item.current_stock - part.quantity)
            await item_repo.save(item)
            movement = InventoryMovement(
                item_id=part.item_id,
                movement_type=MovementType.CONSUMPTION,
                quantity=-part.quantity,
                reference_type="engineer_visit",
                reference_id=visit.id,
                notes=part.description,
            )
            await movement_repo.create(movement)

    return await repo.save(visit)
