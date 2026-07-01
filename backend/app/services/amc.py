from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.amc import AMCContract, AMCAsset, AMCStatus
from app.repositories.base import TenantRepository
from app.schemas.amc import AMCContractCreate, AMCContractUpdate
from app.services.sequences import next_number


class AMCRepository(TenantRepository[AMCContract]):
    model = AMCContract


class AMCAssetRepository(TenantRepository[AMCAsset]):
    model = AMCAsset


async def list_amc(db, tenant_id, offset=0, limit=50):
    return await AMCRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_amc(db, tenant_id, amc_id):
    obj = await AMCRepository(db, tenant_id).get(amc_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AMC contract not found")
    return obj


async def create_amc(db: AsyncSession, tenant_id: UUID, payload: AMCContractCreate) -> AMCContract:
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, tenant_id, payload.company_id)
    repo = AMCRepository(db, tenant_id)
    asset_repo = AMCAssetRepository(db, tenant_id)

    contract = AMCContract(
        company_id=comp_id,
        customer_id=payload.customer_id,
        contract_number=await next_number(db, tenant_id, "amc", "AMC", width=4),
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
    was_active = obj.status == AMCStatus.ACTIVE
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    saved = await repo.save(obj)

    # On activation, auto-generate the preventive-maintenance schedule (SRS 4.9).
    if not was_active and saved.status == AMCStatus.ACTIVE:
        from app.services.pm_schedule import generate_for_contract
        await generate_for_contract(db, tenant_id, saved)
    return saved


async def activate_amc(db, tenant_id, amc_id):
    """Convenience: set contract ACTIVE and generate its PM schedule."""
    repo = AMCRepository(db, tenant_id)
    obj = await repo.get(amc_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AMC contract not found")
    obj.status = AMCStatus.ACTIVE
    saved = await repo.save(obj)
    from app.services.pm_schedule import generate_for_contract
    await generate_for_contract(db, tenant_id, saved)
    return saved


async def render_company_amc_contract_pdf(db: AsyncSession, tenant_id: UUID, amc_id: UUID) -> bytes:
    from app.services.company_template import render_company_document
    from app.services.customer import get_customer
    from app.models.asset import CCTVAsset
    from sqlalchemy import select

    contract = await get_amc(db, tenant_id, amc_id)
    customer = await get_customer(db, tenant_id, contract.customer_id)
    
    # Resolve actual CCTV assets covered
    covered_assets = []
    from app.models.amc import AMCAsset
    res_amc_assets = await db.execute(select(AMCAsset).where(AMCAsset.contract_id == amc_id))
    amc_assets = res_amc_assets.scalars().all()
    if amc_assets:
        asset_ids = [a.asset_id for a in amc_assets]
        r = await db.execute(select(CCTVAsset).where(CCTVAsset.id.in_(asset_ids)))
        covered_assets = [
            {
                "serial_number": a.serial_number,
                "name": a.name,
                "type": a.asset_type,
                "location": a.location or ""
            }
            for a in r.scalars().all()
        ]

    context = {
        "doc": contract,
        "items": covered_assets,
        "customer": customer
    }
    return await render_company_document(db, tenant_id, contract.company_id, "AMC_CONTRACT", context)
