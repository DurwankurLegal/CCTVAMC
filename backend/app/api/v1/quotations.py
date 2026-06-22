from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.quotation import QuotationCreate, QuotationUpdate, QuotationResponse
from app.services import quotation as quotation_service

router = APIRouter()


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
