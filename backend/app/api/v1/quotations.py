from typing import List
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.quotation import QuotationCreate, QuotationUpdate, QuotationResponse
from app.services import quotation as quotation_service

router = APIRouter()


class ConvertToAMCRequest(BaseModel):
    start_date: date
    end_date: date
    preventive_visits_per_year: int = 2


@router.get("", response_model=List[QuotationResponse])
async def list_quotations(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await quotation_service.list_quotations(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(
    payload: QuotationCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("quotations:write")),
):
    return await quotation_service.create_quotation(db, current_user.tenant_id, payload)


@router.get("/{qid}", response_model=QuotationResponse)
async def get_quotation(
    qid: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await quotation_service.get_quotation(db, current_user.tenant_id, qid)


@router.patch("/{qid}", response_model=QuotationResponse)
async def update_quotation(
    qid: UUID, payload: QuotationUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("quotations:write")),
):
    return await quotation_service.update_quotation(db, current_user.tenant_id, qid, payload)


@router.post("/{qid}/approve", response_model=QuotationResponse)
async def approve_quotation(
    qid: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("quotations:write")),
):
    return await quotation_service.set_status(db, current_user.tenant_id, qid, "approved")


@router.post("/{qid}/reject", response_model=QuotationResponse)
async def reject_quotation(
    qid: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("quotations:write")),
):
    return await quotation_service.set_status(db, current_user.tenant_id, qid, "rejected")


@router.post("/{qid}/convert-to-amc")
async def convert_to_amc(
    qid: UUID, payload: ConvertToAMCRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("amc:write")),
):
    contract = await quotation_service.convert_to_amc(
        db, current_user.tenant_id, qid, payload.start_date, payload.end_date,
        payload.preventive_visits_per_year,
    )
    return {"amc_contract_id": str(contract.id), "contract_number": contract.contract_number}


@router.get("/{qid}/pdf")
async def quotation_pdf(
    qid: UUID,
    template: str = "template1",
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download the quotation as a branded PDF."""
    from fastapi import Response
    quote = await quotation_service.get_quotation(db, current_user.tenant_id, qid)
    pdf = await quotation_service.render_company_quotation_pdf(db, quote, template_name=template)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{quote.quotation_number}.pdf"'})
