from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.engineer_visit import (
    EngineerVisitCreate, EngineerVisitResponse,
    EngineerVisitUpdate, CheckinRequest, CheckoutRequest,
)
from app.services import engineer_visit as visit_service
from app.services import document as document_service

router = APIRouter()


@router.post("/media", status_code=201)
async def upload_visit_media(
    visit_id: UUID = Form(...),
    media_type: str = Form("photo"),   # photo | signature
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("engineer_visits:write")),
):
    """Endpoint the mobile app calls to sync photos/signatures captured offline."""
    content = await file.read()
    doc = await document_service.upload_document(
        db, current_user.tenant_id, entity_type="visit", entity_id=visit_id,
        doc_type=media_type, file_name=file.filename or f"{media_type}.bin",
        content=content, content_type=file.content_type, uploaded_by=current_user.user_id,
    )
    await visit_service.attach_media(db, current_user.tenant_id, visit_id, media_type, doc.url)
    return {"id": str(doc.id), "url": doc.url}


@router.get("", response_model=List[EngineerVisitResponse])
async def list_visits(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await visit_service.list_visits(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=EngineerVisitResponse, status_code=201)
async def create_visit(
    payload: EngineerVisitCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("engineer_visits:write")),
):
    return await visit_service.create_visit(
        db, current_user.tenant_id, current_user.user_id, payload
    )


@router.patch("/{visit_id}", response_model=EngineerVisitResponse)
@router.put("/{visit_id}", response_model=EngineerVisitResponse)
async def update_visit(
    visit_id: UUID, payload: EngineerVisitUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("engineer_visits:write")),
):
    """Partial update — admin/manager can correct visit details and override timestamps."""
    return await visit_service.update_visit(db, current_user.tenant_id, visit_id, payload)


@router.get("/{visit_id}", response_model=EngineerVisitResponse)
async def get_visit(
    visit_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await visit_service.get_visit(db, current_user.tenant_id, visit_id)


@router.post("/{visit_id}/checkin", response_model=EngineerVisitResponse)
async def checkin(
    visit_id: UUID, payload: CheckinRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("engineer_visits:write")),
):
    return await visit_service.checkin(db, current_user.tenant_id, visit_id, payload)


@router.post("/{visit_id}/checkout", response_model=EngineerVisitResponse)
async def checkout(
    visit_id: UUID, payload: CheckoutRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("engineer_visits:write")),
):
    return await visit_service.checkout(db, current_user.tenant_id, visit_id, payload)
