from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.rental import (
    RentalUnitCreate, RentalUnitUpdate, RentalUnitResponse,
    RentalContractCreate, RentalContractResponse,
    RentalMovementResponse
)
from app.models.rental import RentalContract, RentalUnit
from app.services import rental as rental_service

router = APIRouter()


class CheckOutPayload(BaseModel):
    rental_unit_id: UUID
    condition: Optional[str] = None
    meter_reading: Optional[str] = None
    notes: Optional[str] = None


class CheckInPayload(BaseModel):
    rental_unit_id: UUID
    condition: Optional[str] = None
    meter_reading: Optional[str] = None
    notes: Optional[str] = None


@router.get("/units", response_model=List[RentalUnitResponse])
async def get_units(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await rental_service.list_units(db, current_user.tenant_id, offset, limit)


@router.post("/units", response_model=RentalUnitResponse, status_code=201)
async def create_unit(
    payload: RentalUnitCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    return await rental_service.create_unit_raw(db, current_user.tenant_id, payload)


@router.patch("/units/{id}", response_model=RentalUnitResponse)
async def update_unit(
    id: UUID, payload: RentalUnitUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    return await rental_service.update_unit(db, current_user.tenant_id, id, payload)


@router.get("/contracts", response_model=List[RentalContractResponse])
async def get_contracts(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await rental_service.list_contracts(db, current_user.tenant_id, offset, limit)


@router.post("/contracts", response_model=RentalContractResponse, status_code=201)
async def create_contract(
    payload: RentalContractCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    return await rental_service.create_rental_contract(db, current_user.tenant_id, payload)


@router.post("/contracts/{id}/activate", response_model=RentalContractResponse)
async def activate_contract(
    id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    stmt = select(RentalContract).where(RentalContract.id == id, RentalContract.tenant_id == current_user.tenant_id).options(selectinload(RentalContract.lines))
    res = await db.execute(stmt)
    contract = res.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    contract.status = "active"
    await db.commit()
    # reload to serialize lines correctly
    stmt = select(RentalContract).where(RentalContract.id == id).options(selectinload(RentalContract.lines))
    res = await db.execute(stmt)
    contract = res.scalar_one()
    return contract


@router.post("/contracts/{id}/checkout", response_model=RentalMovementResponse)
async def checkout_unit(
    id: UUID, payload: CheckOutPayload, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    stmt = select(RentalContract).where(RentalContract.id == id, RentalContract.tenant_id == current_user.tenant_id).options(selectinload(RentalContract.lines))
    res = await db.execute(stmt)
    contract = res.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    unit = await db.get(RentalUnit, payload.rental_unit_id)
    if not unit or unit.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental unit not found")

    # Check if unit is available
    available = await rental_service.check_unit_availability(
        db, current_user.tenant_id, unit.id, contract.start_date, contract.end_date
    )
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rental unit is not available (overlapping contract exists or status not available)"
        )

    # Assign unit to first unassigned contract line of matching product
    line_found = False
    for line in contract.lines:
        if line.product_id == unit.product_id and line.rental_unit_id is None:
            line.rental_unit_id = unit.id
            line_found = True
            break

    if not line_found:
        # Fallback to assign to any matching line
        for line in contract.lines:
            if line.product_id == unit.product_id:
                line.rental_unit_id = unit.id
                line_found = True
                break

    if not line_found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No matching product line found in contract for this unit type"
        )

    from app.schemas.rental import RentalMovementCreate as RMCreate
    m_payload = RMCreate(
        rental_contract_id=contract.id,
        rental_unit_id=unit.id,
        movement_type="check_out",
        movement_date=date.today(),
        condition=payload.condition,
        meter_reading=payload.meter_reading,
        notes=payload.notes
    )

    movement = await rental_service.record_rental_movement(
        db, current_user.tenant_id, current_user.user_id, m_payload
    )
    await db.commit()
    return movement


@router.post("/contracts/{id}/checkin", response_model=RentalMovementResponse)
async def checkin_unit(
    id: UUID, payload: CheckInPayload, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("rentals:write")),
):
    stmt = select(RentalContract).where(RentalContract.id == id, RentalContract.tenant_id == current_user.tenant_id).options(selectinload(RentalContract.lines))
    res = await db.execute(stmt)
    contract = res.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    unit = await db.get(RentalUnit, payload.rental_unit_id)
    if not unit or unit.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental unit not found")

    from app.schemas.rental import RentalMovementCreate as RMCreate
    m_payload = RMCreate(
        rental_contract_id=contract.id,
        rental_unit_id=unit.id,
        movement_type="check_in",
        movement_date=date.today(),
        condition=payload.condition,
        meter_reading=payload.meter_reading,
        notes=payload.notes
    )

    movement = await rental_service.record_rental_movement(
        db, current_user.tenant_id, current_user.user_id, m_payload
    )
    await db.commit()
    return movement


@router.post("/contracts/generate-billing")
async def run_billing(
    billing_date: Optional[date] = None, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    b_date = billing_date or date.today()
    invoices = await rental_service.generate_monthly_rental_billing(db, current_user.tenant_id, b_date)
    return {
        "message": f"Successfully processed recurring rental billing for {b_date.strftime('%B %Y')}",
        "invoices_generated": len(invoices)
    }
