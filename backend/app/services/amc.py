from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.amc import AMCContract, AMCAsset, AMCStatus
from app.repositories.base import TenantRepository
from app.schemas.amc import AMCContractCreate, AMCContractUpdate


class AMCRepository(TenantRepository[AMCContract]):
    model = AMCContract


class AMCAssetRepository(TenantRepository[AMCAsset]):
    model = AMCAsset


_AMC_SEQ: dict[UUID, int] = {}


def _next_contract_number(tenant_id: UUID) -> str:
    _AMC_SEQ[tenant_id] = _AMC_SEQ.get(tenant_id, 0) + 1
    year = datetime.now(timezone.utc).year
    return f"AMC-{str(tenant_id)[:4].upper()}-{year}-{_AMC_SEQ[tenant_id]:04d}"


async def list_amc(db, tenant_id, offset=0, limit=50):
    return await AMCRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_amc(db, tenant_id, amc_id):
    obj = await AMCRepository(db, tenant_id).get(amc_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AMC contract not found")
    return obj


async def create_amc(db: AsyncSession, tenant_id: UUID, payload: AMCContractCreate) -> AMCContract:
    repo = AMCRepository(db, tenant_id)
    asset_repo = AMCAssetRepository(db, tenant_id)

    contract = AMCContract(
        customer_id=payload.customer_id,
        contract_number=_next_contract_number(tenant_id),
        start_date=payload.start_date,
        end_date=payload.end_date,
        annual_amount=payload.annual_amount,
        payment_frequency=payload.payment_frequency,
        terms=payload.terms,
        preventive_visits_per_year=payload.preventive_visits_per_year,
        status=AMCStatus.DRAFT,
    )
    contract = await repo.create(contract)

    # Link assets
    for asset_id in payload.asset_ids:
        link = AMCAsset(contract_id=contract.id, asset_id=asset_id)
        await asset_repo.create(link)

    return contract


async def update_amc(db, tenant_id, amc_id, payload: AMCContractUpdate):
    repo = AMCRepository(db, tenant_id)
    obj = await repo.get(amc_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AMC contract not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    return await repo.save(obj)
