from typing import List
from datetime import date
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.amc import AMCContractCreate, AMCContractUpdate, AMCContractResponse
from app.services import amc as amc_service
from app.services import pm_schedule as pm_service

router = APIRouter()


class RescheduleRequest(BaseModel):
    new_date: date
    reason: str


class SkipRequest(BaseModel):
    reason: str


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
    current_user: CurrentUser = Depends(require_permission("amc:write")),
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
    current_user: CurrentUser = Depends(require_permission("amc:write")),
):
    return await amc_service.update_amc(db, current_user.tenant_id, amc_id, payload)


@router.post("/{amc_id}/activate", response_model=AMCContractResponse)
async def activate_amc(
    amc_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("amc:write")),
):
    """Activate a contract and auto-generate its preventive-maintenance schedule."""
    return await amc_service.activate_amc(db, current_user.tenant_id, amc_id)


# ── Preventive maintenance schedule (SRS 4.9) ─────────────────
@router.get("/{amc_id}/pm-schedule")
async def list_pm_schedule(
    amc_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = await pm_service.list_for_contract(db, current_user.tenant_id, amc_id)
    summary = await pm_service.completion_summary(db, current_user.tenant_id, amc_id)
    return {"summary": summary, "visits": [
        {"id": str(r.id), "sequence_no": r.sequence_no, "scheduled_date": str(r.scheduled_date),
         "status": r.status, "reason_code": r.reason_code} for r in rows]}


@router.post("/pm-schedule/{pm_id}/reschedule")
async def reschedule_pm(
    pm_id: UUID, payload: RescheduleRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("amc:write")),
):
    pm = await pm_service.reschedule(db, current_user.tenant_id, pm_id, payload.new_date, payload.reason)
    return {"id": str(pm.id), "status": pm.status, "scheduled_date": str(pm.scheduled_date)}


@router.post("/pm-schedule/{pm_id}/skip")
async def skip_pm(
    pm_id: UUID, payload: SkipRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("amc:write")),
):
    pm = await pm_service.skip(db, current_user.tenant_id, pm_id, payload.reason)
    return {"id": str(pm.id), "status": pm.status}


@router.get("/{amc_id}/pdf")
async def amc_contract_pdf(
    amc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download the AMC contract agreement as a PDF."""
    from fastapi import Response
    contract = await amc_service.get_amc(db, current_user.tenant_id, amc_id)
    pdf = await amc_service.render_company_amc_contract_pdf(db, current_user.tenant_id, amc_id)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AMC-{contract.contract_number}.pdf"'}
    )
