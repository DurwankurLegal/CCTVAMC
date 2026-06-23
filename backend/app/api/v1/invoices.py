from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from app.services import invoice as invoice_service

router = APIRouter()


@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await invoice_service.list_invoices(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    payload: InvoiceCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    return await invoice_service.create_invoice(db, current_user.tenant_id, payload)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await invoice_service.get_invoice(db, current_user.tenant_id, invoice_id)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID, payload: InvoiceUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    return await invoice_service.update_invoice(db, current_user.tenant_id, invoice_id, payload)


@router.post("/{invoice_id}/credit-note", response_model=InvoiceResponse, status_code=201)
async def create_credit_note(
    invoice_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoices:write")),
):
    """Raise a GST credit note against an existing invoice."""
    return await invoice_service.create_credit_note(db, current_user.tenant_id, invoice_id)


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(
    invoice_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download the invoice as a GST-compliant PDF (SRS 4.13)."""
    inv = await invoice_service.get_invoice(db, current_user.tenant_id, invoice_id)
    pdf = invoice_service.render_pdf(inv)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{inv.invoice_number}.pdf"'})
