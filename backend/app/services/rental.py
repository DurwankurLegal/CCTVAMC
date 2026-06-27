from uuid import UUID
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.rental import RentalUnit, RentalContract, RentalContractLine, RentalMovement
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.invoice import Invoice, InvoiceType
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.services.sequences import next_number
from app.services.gst import compute_gst_totals, grand_total
from app.schemas.rental import RentalUnitCreate, RentalContractCreate, RentalMovementCreate
from app.schemas.invoice import InvoiceCreate
from app.services.invoice import create_invoice


class RentalUnitRepository(TenantRepository[RentalUnit]):
    model = RentalUnit


class RentalContractRepository(TenantRepository[RentalContract]):
    model = RentalContract


class RentalMovementRepository(TenantRepository[RentalMovement]):
    model = RentalMovement


list_units, get_unit_raw, create_unit_raw, update_unit = make_crud(RentalUnitRepository, RentalUnit)
_list_contracts, _get_contract_raw, create_contract_raw, update_contract = make_crud(RentalContractRepository, RentalContract)
list_movements, get_movement_raw, create_movement_raw, update_movement = make_crud(RentalMovementRepository, RentalMovement)


async def list_contracts(db: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50) -> List[RentalContract]:
    stmt = (
        select(RentalContract)
        .where(RentalContract.tenant_id == tenant_id)
        .options(selectinload(RentalContract.lines))
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_contract(db: AsyncSession, tenant_id: UUID, contract_id: UUID) -> Optional[RentalContract]:
    stmt = (
        select(RentalContract)
        .where(RentalContract.id == contract_id, RentalContract.tenant_id == tenant_id)
        .options(selectinload(RentalContract.lines))
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def check_unit_availability(db: AsyncSession, tenant_id: UUID, unit_id: UUID, start_date: date, end_date: date) -> bool:
    unit_res = await db.execute(
        select(RentalUnit).where(RentalUnit.id == unit_id, RentalUnit.tenant_id == tenant_id)
    )
    unit = unit_res.scalar_one_or_none()
    if not unit or not unit.is_active or unit.status in ("maintenance", "retired"):
        return False

    overlap_res = await db.execute(
        select(RentalContractLine)
        .join(RentalContract)
        .where(
            RentalContractLine.rental_unit_id == unit_id,
            RentalContract.tenant_id == tenant_id,
            RentalContract.status.in_(["booked", "active"]),
            RentalContract.start_date <= end_date,
            RentalContract.end_date >= start_date
        )
    )
    overlaps = overlap_res.scalars().all()
    return len(overlaps) == 0


async def create_rental_contract(db: AsyncSession, tenant_id: UUID, payload: RentalContractCreate) -> RentalContract:
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    origin_state = tenant.settings.get("state_code") if tenant else None

    lines_db = []
    subtotal = 0.0
    cgst = 0.0
    sgst = 0.0
    igst = 0.0

    for item in payload.lines:
        qty = item.quantity
        price = item.unit_price
        amt = price * qty
        gst_rate = item.gst_rate

        line_items_temp = [{
            "quantity": qty,
            "unit_price": price,
            "gst_rate": gst_rate
        }]

        l_sub, l_cgst, l_sgst, l_igst = compute_gst_totals(
            line_items_temp,
            origin_state if origin_state == "27" else "29",
            origin_state
        )

        line_db = RentalContractLine(
            tenant_id=tenant_id,
            product_id=item.product_id,
            rental_unit_id=item.rental_unit_id,
            quantity=qty,
            unit_price=price,
            gst_rate=gst_rate,
            cgst_amount=l_cgst,
            sgst_amount=l_sgst,
            igst_amount=l_igst,
            total_amount=grand_total(l_sub, l_cgst, l_sgst, l_igst)
        )
        lines_db.append(line_db)

        subtotal += l_sub
        cgst += l_cgst
        sgst += l_sgst
        igst += l_igst

    contract = RentalContract(
        tenant_id=tenant_id,
        contract_number=await next_number(db, tenant_id, "rental_contract", "RC"),
        customer_id=payload.customer_id,
        site_id=payload.site_id,
        company_id=payload.company_id,
        status="booked",
        start_date=payload.start_date,
        end_date=payload.end_date,
        billing_cycle=payload.billing_cycle,
        deposit_amount=payload.deposit_amount,
        deposit_status=payload.deposit_status,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=grand_total(subtotal, cgst, sgst, igst),
        notes=payload.notes,
        lines=lines_db
    )

    db.add(contract)
    await db.flush()

    # Preload lines relationship to prevent async RLS lazy loading exception
    stmt = (
        select(RentalContract)
        .where(RentalContract.id == contract.id)
        .options(selectinload(RentalContract.lines))
    )
    res = await db.execute(stmt)
    contract = res.scalar_one()
    return contract


async def record_rental_movement(db: AsyncSession, tenant_id: UUID, user_id: UUID, payload: RentalMovementCreate) -> RentalMovement:
    unit_res = await db.execute(
        select(RentalUnit).where(RentalUnit.id == payload.rental_unit_id, RentalUnit.tenant_id == tenant_id)
    )
    unit = unit_res.scalar_one_or_none()
    if not unit:
        raise ValueError("Rental unit not found")

    movement = RentalMovement(
        tenant_id=tenant_id,
        rental_contract_id=payload.rental_contract_id,
        rental_unit_id=payload.rental_unit_id,
        movement_type=payload.movement_type,
        movement_date=payload.movement_date,
        condition=payload.condition,
        notes=payload.notes,
        charges=payload.charges,
        recorded_by=user_id
    )
    db.add(movement)

    if payload.movement_type == "check_out":
        unit.status = "on_rent"
        if payload.condition:
            unit.condition = payload.condition
    elif payload.movement_type == "check_in":
        if payload.condition in ("poor", "maintenance"):
            unit.status = "maintenance"
        else:
            unit.status = "available"
        if payload.condition:
            unit.condition = payload.condition

    await db.flush()
    return movement


async def generate_monthly_rental_billing(db: AsyncSession, tenant_id: UUID, billing_date: date) -> List[Invoice]:
    contracts_res = await db.execute(
        select(RentalContract)
        .where(
            RentalContract.tenant_id == tenant_id,
            RentalContract.status == "active",
            RentalContract.billing_cycle == "monthly",
            RentalContract.start_date <= billing_date,
            RentalContract.end_date >= billing_date
        )
        .options(selectinload(RentalContract.lines))
    )
    contracts = contracts_res.scalars().all()
    invoices_created = []

    target_month_year = billing_date.strftime("%B %Y")

    for contract in contracts:
        note_identifier = f"Rental Billing for Contract {contract.contract_number} - {target_month_year}"
        existing_res = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.customer_id == contract.customer_id,
                Invoice.notes.like(f"%{note_identifier}%")
            )
        )
        if existing_res.scalars().first():
            continue

        inv_lines = []
        for line in contract.lines:
            prod = await db.get(Product, line.product_id)
            prod_name = prod.name if prod else "Rental Equipment"
            prod_sku = prod.sku if prod else "RENTAL"

            inv_lines.append({
                "description": f"{prod_name} (SKU: {prod_sku}) - Monthly Rent",
                "quantity": line.quantity,
                "unit_price": float(line.unit_price),
                "gst_rate": float(line.gst_rate),
                "amount": float(line.total_amount)
            })

        inv_payload = InvoiceCreate(
            company_id=contract.company_id,
            customer_id=contract.customer_id,
            invoice_type=InvoiceType.TAX_INVOICE,
            invoice_date=billing_date,
            due_date=billing_date,
            supply_state_code="27",
            line_items=inv_lines,
            notes=note_identifier
        )

        invoice = await create_invoice(db, tenant_id, inv_payload)
        invoices_created.append(invoice)

    await db.commit()
    return invoices_created
