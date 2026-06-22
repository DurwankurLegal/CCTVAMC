"""New-installation workflow (SRS 4.5).

Generate a work order (optionally from a quotation), run the survey, progress
through job states, and on handover (OTP-verified) auto-create the AMC contract
and register asset warranties.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone, date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.installation import Installation, InstallationStatus
from app.models.asset import CCTVAsset
from app.repositories.base import TenantRepository
from app.schemas.installation import InstallationCreate, SurveyUpdate, InstallationUpdate, HandoverRequest
from app.services.sequences import next_number


class InstallationRepository(TenantRepository[Installation]):
    model = Installation


async def list_installations(db, tenant_id, offset=0, limit=50):
    return await InstallationRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_installation(db, tenant_id, inst_id) -> Installation:
    obj = await InstallationRepository(db, tenant_id).get(inst_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installation not found")
    return obj


async def create_installation(db: AsyncSession, tenant_id: UUID, payload: InstallationCreate) -> Installation:
    inst = Installation(
        work_order_number=await next_number(db, tenant_id, "installation", "WO"),
        customer_id=payload.customer_id,
        site_id=payload.site_id,
        quotation_id=payload.quotation_id,
        assigned_technician_id=payload.assigned_technician_id,
        target_completion_date=payload.target_completion_date,
        status=InstallationStatus.SURVEY_PENDING,
    )
    return await InstallationRepository(db, tenant_id).create(inst)


async def record_survey(db, tenant_id, inst_id, payload: SurveyUpdate) -> Installation:
    repo = InstallationRepository(db, tenant_id)
    inst = await get_installation(db, tenant_id, inst_id)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    inst.status = InstallationStatus.SURVEY_DONE
    return await repo.save(inst)


async def update_installation(db, tenant_id, inst_id, payload: InstallationUpdate) -> Installation:
    repo = InstallationRepository(db, tenant_id)
    inst = await get_installation(db, tenant_id, inst_id)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    return await repo.save(inst)


async def request_handover_otp(db, tenant_id, inst_id) -> str:
    repo = InstallationRepository(db, tenant_id)
    inst = await get_installation(db, tenant_id, inst_id)
    inst.handover_otp = f"{random.randint(0, 999999):06d}"
    await repo.save(inst)
    return inst.handover_otp


async def handover(db: AsyncSession, tenant_id: UUID, inst_id: UUID, payload: HandoverRequest) -> Installation:
    """Verify OTP, mark handed over, auto-create AMC and register warranties."""
    repo = InstallationRepository(db, tenant_id)
    inst = await get_installation(db, tenant_id, inst_id)
    if not inst.handover_otp or payload.otp != inst.handover_otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid handover OTP")

    # Auto-create AMC contract (SRS 4.5 -> 4.7) and activate it (generates PM schedule).
    from app.services.amc import AMCRepository, AMCStatus
    from app.models.amc import AMCContract
    start = date.today()
    end = start + timedelta(days=30 * payload.amc_months)
    contract = AMCContract(
        customer_id=inst.customer_id,
        contract_number=await next_number(db, tenant_id, "amc", "AMC", width=4),
        start_date=start, end_date=end,
        annual_amount=payload.amc_annual_amount,
        preventive_visits_per_year=payload.preventive_visits_per_year,
        status=AMCStatus.ACTIVE,
    )
    contract = await AMCRepository(db, tenant_id).create(contract)
    from app.services.pm_schedule import generate_for_contract
    await generate_for_contract(db, tenant_id, contract)

    # Register manufacturer warranty (1 year) on the site's assets if unset.
    if inst.site_id:
        assets = (await db.execute(
            select(CCTVAsset).where(CCTVAsset.tenant_id == tenant_id, CCTVAsset.site_id == inst.site_id)
        )).scalars().all()
        for a in assets:
            if a.warranty_expiry is None:
                a.installation_date = a.installation_date or start
                a.warranty_expiry = start + timedelta(days=365)

    inst.status = InstallationStatus.HANDED_OVER
    inst.handed_over_at = datetime.now(timezone.utc)
    inst.amc_contract_id = contract.id
    return await repo.save(inst)
