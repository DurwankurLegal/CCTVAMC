"""Preventive-maintenance scheduling (SRS 4.9).

When an AMC contract is activated, evenly-spaced PM visits are generated across
the contract period based on ``preventive_visits_per_year``. Coordinators can
reschedule or skip planned visits with a reason code.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.pm_schedule import PMSchedule, PMStatus
from app.models.amc import AMCContract
from app.repositories.base import TenantRepository


class PMRepository(TenantRepository[PMSchedule]):
    model = PMSchedule


async def generate_for_contract(db: AsyncSession, tenant_id: UUID, contract: AMCContract) -> list[PMSchedule]:
    """Generate evenly-spaced PM visits for a contract. Idempotent: does nothing
    if a schedule already exists for the contract."""
    existing = (await db.execute(
        select(PMSchedule).where(
            PMSchedule.tenant_id == tenant_id,
            PMSchedule.amc_contract_id == contract.id,
        )
    )).scalars().first()
    if existing:
        return []

    n = contract.preventive_visits_per_year or 0
    if n <= 0 or not contract.start_date or not contract.end_date:
        return []

    total_days = (contract.end_date - contract.start_date).days
    if total_days <= 0:
        return []
    step = max(1, total_days // n)

    repo = PMRepository(db, tenant_id)
    created = []
    for i in range(n):
        sched_date = contract.start_date + timedelta(days=step * (i + 1))
        if sched_date > contract.end_date:
            sched_date = contract.end_date
        created.append(await repo.create(PMSchedule(
            amc_contract_id=contract.id, sequence_no=i + 1,
            scheduled_date=sched_date, status=PMStatus.PLANNED,
        )))
    return created


async def list_for_contract(db: AsyncSession, tenant_id: UUID, contract_id: UUID):
    return list((await db.execute(
        select(PMSchedule).where(
            PMSchedule.tenant_id == tenant_id,
            PMSchedule.amc_contract_id == contract_id,
        ).order_by(PMSchedule.sequence_no)
    )).scalars().all())


async def reschedule(db: AsyncSession, tenant_id: UUID, pm_id: UUID, new_date: date, reason: str) -> PMSchedule:
    repo = PMRepository(db, tenant_id)
    pm = await repo.get(pm_id)
    if not pm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PM visit not found")
    pm.scheduled_date = new_date
    pm.status = PMStatus.RESCHEDULED
    pm.reason_code = reason
    return await repo.save(pm)


async def skip(db: AsyncSession, tenant_id: UUID, pm_id: UUID, reason: str) -> PMSchedule:
    repo = PMRepository(db, tenant_id)
    pm = await repo.get(pm_id)
    if not pm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PM visit not found")
    pm.status = PMStatus.SKIPPED
    pm.reason_code = reason
    return await repo.save(pm)


async def completion_summary(db: AsyncSession, tenant_id: UUID, contract_id: UUID) -> dict:
    rows = await list_for_contract(db, tenant_id, contract_id)
    done = sum(1 for r in rows if r.status == PMStatus.DONE)
    return {"committed": len(rows), "completed": done,
            "remaining": sum(1 for r in rows if r.status == PMStatus.PLANNED)}
