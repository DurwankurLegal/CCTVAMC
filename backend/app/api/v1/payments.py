from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentUpdate
from app.services import payment as payment_service

router = APIRouter()


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await payment_service.list_payments(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=PaymentResponse, status_code=201)
async def record_payment(
    payload: PaymentCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    return await payment_service.record_payment(db, current_user.tenant_id, payload)


@router.get("/ageing")
async def payment_ageing(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Receivables ageing buckets: current / 30d / 60d / 90d+"""
    return await payment_service.get_payment_ageing(db, current_user.tenant_id)


@router.patch("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID, payload: PaymentUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payments:write")),
):
    return await payment_service.update_payment(db, current_user.tenant_id, payment_id, payload)


@router.get("/{payment_id}/receipt")
async def payment_receipt(
    payment_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download a payment receipt PDF (SRS 4.14)."""
    payment = await payment_service.get_payment(db, current_user.tenant_id, payment_id)
    pdf = payment_service.render_receipt(payment)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="receipt-{payment_id}.pdf"'})
