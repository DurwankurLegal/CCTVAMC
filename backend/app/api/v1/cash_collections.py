from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.cash_collection import CashCollectionCreate, CashCollectionAction, CashCollectionResponse, CashCollectionUpdate
from app.models.cash_collection import CashCollection
from app.services import cash_collection as cash_service

router = APIRouter()

@router.get("", response_model=List[CashCollectionResponse])
async def list_cash_collections(
    employee_id: UUID = Query(None),
    company_id: UUID = Query(None),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = cash_service.CashCollectionRepository(db, current_user.tenant_id)
    await repo._set_rls_context()
    
    stmt = select(CashCollection).where(CashCollection.tenant_id == current_user.tenant_id)
    
    # Scoping for technicians: they can only see their own collections
    if current_user.role == "technician":
        stmt = stmt.where(CashCollection.employee_id == current_user.user_id)
    elif employee_id:
        stmt = stmt.where(CashCollection.employee_id == employee_id)
        
    if company_id:
        stmt = stmt.where(CashCollection.company_id == company_id)
    if status:
        stmt = stmt.where(CashCollection.status == status)
        
    stmt = stmt.order_by(CashCollection.collected_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

@router.post("", response_model=CashCollectionResponse, status_code=201)
async def create_cash_collection(
    payload: CashCollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await cash_service.create_cash_collection(
        db, current_user.tenant_id, current_user.user_id, payload
    )

@router.post("/{cash_collection_id}/action", response_model=CashCollectionResponse)
async def verify_cash_collection(
    cash_collection_id: UUID,
    payload: CashCollectionAction,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),  # Require admin/manager level permission
):
    return await cash_service.review_cash_collection(
        db, current_user.tenant_id, cash_collection_id, current_user.user_id, payload
    )


@router.put("/{cash_collection_id}", response_model=CashCollectionResponse)
async def update_cash_collection(
    cash_collection_id: UUID,
    payload: CashCollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),
):
    return await cash_service.update_cash_collection(
        db, current_user.tenant_id, cash_collection_id, payload
    )


@router.post("/{cash_collection_id}/media", status_code=201)
async def upload_receipt_photo(
    cash_collection_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from fastapi import UploadFile, File
    from app.services import document as document_service
    
    collection = await cash_service.get_cash_collection(db, current_user.tenant_id, cash_collection_id)
    
    doc = await document_service.upload_document(
        db, current_user.tenant_id, entity_type="cash_collection", entity_id=cash_collection_id,
        doc_type="receipt", file_name=file.filename or "receipt.jpg",
        content=await file.read(), content_type=file.content_type,
        uploaded_by=current_user.user_id
    )
    
    collection.receipt_photo_url = doc.url
    await cash_service.CashCollectionRepository(db, current_user.tenant_id).save(collection)
    
    return {"url": doc.url}
