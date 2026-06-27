from typing import List, Optional, Any
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.models.sales_order import SalesOrder, SalesOrderStatus
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.asset import CCTVAsset, AssetStatus
from app.models.customer import CustomerSite
from app.models.inventory import MovementType
from app.services.sequences import next_number
from app.services.gst import compute_gst_totals, grand_total
from app.services.inventory import adjust_stock, StockAdjustment
from app.schemas.sales_order import SalesOrderCreate, SalesOrderResponse
from app.schemas.invoice import InvoiceCreate
from app.services.invoice import create_invoice
from app.models.invoice import InvoiceType

router = APIRouter()


class SalesOrderFulfil(BaseModel):
    line_items: Optional[List[Any]] = None


@router.get("", response_model=List[SalesOrderResponse])
async def list_orders(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.tenant_id == current_user.tenant_id)
        .offset(offset).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{id}", response_model=SalesOrderResponse)
async def get_order(
    id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    return order


@router.post("", response_model=SalesOrderResponse, status_code=201)
async def create_order(
    payload: SalesOrderCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales_orders:write")),
):
    # Fetch tenant for state code
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    origin_state = tenant.settings.get("state_code") if tenant else None

    # Auto-resolve product pricing and details from catalog
    new_line_items = []
    for item in payload.line_items:
        prod_id = item.get("product_id")
        qty = int(item.get("quantity", 1))
        price = item.get("unit_price")

        prod = None
        if prod_id:
            try:
                p_uuid = UUID(str(prod_id))
                prod_res = await db.execute(
                    select(Product).where(Product.id == p_uuid, Product.tenant_id == current_user.tenant_id)
                )
                prod = prod_res.scalar_one_or_none()
            except ValueError:
                pass

        if prod:
            gst_rate = float(prod.gst_rate if prod.gst_rate is not None else 18.0)
            unit_price = float(price if price is not None else (prod.sale_price or 0.0))
            amt = unit_price * qty
            new_line_items.append({
                "product_id": str(prod.id),
                "name": prod.name,
                "sku": prod.sku,
                "quantity": qty,
                "unit_price": unit_price,
                "gst_rate": gst_rate,
                "amount": amt,
                "serials": item.get("serials", []),
            })
        else:
            unit_price = float(price if price is not None else item.get("unit_price", 0.0))
            amt = unit_price * qty
            new_line_items.append({
                "name": item.get("name", "Unknown SKU"),
                "quantity": qty,
                "unit_price": unit_price,
                "gst_rate": float(item.get("gst_rate", 18.0)),
                "amount": amt,
                "serials": item.get("serials", []),
            })

    subtotal, cgst, sgst, igst = compute_gst_totals(
        new_line_items,
        payload.supply_state_code,
        origin_state,
    )

    order = SalesOrder(
        tenant_id=current_user.tenant_id,
        order_number=await next_number(db, current_user.tenant_id, "sales_order", "SO"),
        customer_id=payload.customer_id,
        quotation_id=payload.quotation_id,
        order_date=payload.order_date,
        delivery_date=payload.delivery_date,
        line_items=new_line_items,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=grand_total(subtotal, cgst, sgst, igst),
        supply_state_code=payload.supply_state_code,
        notes=payload.notes,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


@router.post("/{id}/confirm", response_model=SalesOrderResponse)
async def confirm_order(
    id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales_orders:write")),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    if order.status != SalesOrderStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already confirmed or processed")
    order.status = SalesOrderStatus.CONFIRMED
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{id}/fulfil", response_model=SalesOrderResponse)
async def fulfil_order(
    id: UUID, payload: SalesOrderFulfil, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales_orders:write")),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    if order.status != SalesOrderStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must be confirmed before fulfilment")

    updated_items = payload.line_items if payload.line_items is not None else order.line_items

    # Process and adjust stock levels
    for item in updated_items:
        prod_id = item.get("product_id")
        qty = int(item.get("quantity", 1))
        serials = item.get("serials", [])

        prod = None
        if prod_id:
            try:
                p_uuid = UUID(str(prod_id))
                prod_res = await db.execute(
                    select(Product).where(Product.id == p_uuid, Product.tenant_id == current_user.tenant_id)
                )
                prod = prod_res.scalar_one_or_none()
            except ValueError:
                pass

        if prod:
            if prod.is_serial_tracked:
                if len(serials) != qty:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{prod.name}' is serial-tracked. Exactly {qty} serial(s) must be provided."
                    )

            # Deduct from inventory stock
            if prod.inventory_item_id:
                adj = StockAdjustment(
                    item_id=prod.inventory_item_id,
                    quantity=-qty,
                    movement_type=MovementType.SALE,
                    reference_type="sales_order",
                    reference_id=order.id,
                    notes=f"Sales Order Fulfilment {order.order_number}"
                )
                await adjust_stock(db, current_user.tenant_id, adj)

            # Auto-register serials as customer site assets
            if serials:
                site_res = await db.execute(
                    select(CustomerSite).where(
                        CustomerSite.customer_id == order.customer_id,
                        CustomerSite.tenant_id == current_user.tenant_id
                    )
                )
                site = site_res.scalars().first()
                if site:
                    for s in serials:
                        asset = CCTVAsset(
                            tenant_id=current_user.tenant_id,
                            site_id=site.id,
                            serial_number=s,
                            make=prod.brand,
                            model=prod.model,
                            asset_type=prod.category,
                            installation_date=date.today(),
                            status=AssetStatus.ACTIVE
                        )
                        db.add(asset)

    order.line_items = updated_items
    order.status = SalesOrderStatus.FULFILLED
    order.fulfilled_at = date.today()
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{id}/cancel", response_model=SalesOrderResponse)
async def cancel_order(
    id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales_orders:write")),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    if order.status == SalesOrderStatus.FULFILLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fulfilled order cannot be cancelled")

    order.status = SalesOrderStatus.CANCELLED
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{id}/invoice")
async def invoice_order(
    id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    if order.status not in (SalesOrderStatus.CONFIRMED, SalesOrderStatus.FULFILLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must be confirmed or fulfilled first")
    if order.invoice_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already generated for this sales order")

    # Resolve company
    from app.services.company import resolve_company_id
    comp_id = await resolve_company_id(db, current_user.tenant_id, None)

    # Convert line items format to mirror invoices expect
    inv_lines = []
    for item in order.line_items:
        inv_lines.append({
            "description": f"{item.get('name')} (SKU: {item.get('sku')})" + (f" - Serials: {', '.join(item.get('serials'))}" if item.get('serials') else ""),
            "quantity": item.get("quantity", 1),
            "unit_price": item.get("unit_price", 0.0),
            "gst_rate": item.get("gst_rate", 18.0),
            "amount": item.get("amount", 0.0)
        })

    inv_payload = InvoiceCreate(
        company_id=comp_id,
        customer_id=order.customer_id,
        invoice_type=InvoiceType.TAX_INVOICE,
        invoice_date=date.today(),
        due_date=date.today(),
        supply_state_code=order.supply_state_code or "27",
        line_items=inv_lines,
        notes=f"Generated from Sales Order {order.order_number}"
    )

    inv = await create_invoice(db, current_user.tenant_id, inv_payload)
    order.invoice_id = inv.id
    await db.commit()
    await db.refresh(order)

    return {"invoice_id": str(inv.id), "invoice_number": inv.invoice_number}
