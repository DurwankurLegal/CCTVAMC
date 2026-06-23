from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.engineer_visit import EngineerVisit
from app.models.inventory import InventoryItem, InventoryMovement, MovementType
from app.repositories.base import TenantRepository
from app.schemas.engineer_visit import EngineerVisitCreate, EngineerVisitUpdate, CheckinRequest, CheckoutRequest


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


async def create_visit(db: AsyncSession, tenant_id: UUID, current_user_id: UUID,
                       payload: EngineerVisitCreate) -> EngineerVisit:
    # Allow coordinator/admin to assign visit to a specific technician; fallback to self.
    assigned_technician = payload.technician_id or current_user_id
    visit = EngineerVisit(
        ticket_id=payload.ticket_id,
        amc_contract_id=payload.amc_contract_id,
        technician_id=assigned_technician,
        visit_type=payload.visit_type,
    )
    return await VisitRepository(db, tenant_id).create(visit)


async def update_visit(db: AsyncSession, tenant_id: UUID, visit_id: UUID,
                       payload: EngineerVisitUpdate) -> EngineerVisit:
    """Partial update — only non-None fields in payload are applied."""
    repo = VisitRepository(db, tenant_id)
    visit = await repo.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(visit, field, value)

    return await repo.save(visit)


async def checkin(db: AsyncSession, tenant_id: UUID, visit_id: UUID,
                  payload: CheckinRequest) -> EngineerVisit:
    repo = VisitRepository(db, tenant_id)
    visit = await repo.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.checkin_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in")
    await _validate_geofence(db, tenant_id, visit, payload.lat, payload.lng)
    visit.checkin_at = datetime.now(timezone.utc)
    visit.checkin_lat = payload.lat
    visit.checkin_lng = payload.lng
    return await repo.save(visit)


# Max allowed distance (km) between technician check-in and the site.
GEOFENCE_RADIUS_KM = 1.0


async def _validate_geofence(db, tenant_id, visit, lat, lng):
    """Reject a check-in that is implausibly far from the ticket's site (SRS 4.10).
    Skips silently when coordinates are unavailable."""
    if lat is None or lng is None or not visit.ticket_id:
        return
    from app.models.service_ticket import ServiceTicket
    from app.models.customer import CustomerSite
    ticket = (await db.execute(
        select(ServiceTicket).where(ServiceTicket.id == visit.ticket_id,
                                    ServiceTicket.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not ticket or not ticket.site_id:
        return
    site = (await db.execute(
        select(CustomerSite).where(CustomerSite.id == ticket.site_id,
                                   CustomerSite.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not site or site.latitude is None or site.longitude is None:
        return
    if _haversine_km(lat, lng, site.latitude, site.longitude) > GEOFENCE_RADIUS_KM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in location is too far from the site",
        )


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    from math import radians, sin, cos, asin, sqrt
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


async def attach_media(db: AsyncSession, tenant_id: UUID, visit_id: UUID,
                       media_type: str, url: str) -> EngineerVisit:
    repo = VisitRepository(db, tenant_id)
    visit = await repo.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if media_type == "signature":
        visit.signature_url = url
    else:
        visit.photo_urls = (visit.photo_urls or []) + [url]
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
