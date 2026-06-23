from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.services import document as document_service

router = APIRouter()


@router.post("", status_code=201)
async def upload_document(
    entity_type: str = Form(...),
    entity_id: UUID = Form(...),
    doc_type: str = Form("other"),
    notes: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    content = await file.read()
    doc = await document_service.upload_document(
        db, current_user.tenant_id, entity_type=entity_type, entity_id=entity_id,
        doc_type=doc_type, file_name=file.filename or "upload", content=content,
        content_type=file.content_type, uploaded_by=current_user.user_id, notes=notes,
    )
    return {"id": str(doc.id), "url": doc.url, "s3_key": doc.s3_key}


@router.get("")
async def list_documents(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    docs = await document_service.list_documents(db, current_user.tenant_id, entity_type, entity_id)
    return [{"id": str(d.id), "doc_type": d.doc_type, "file_name": d.file_name, "url": d.url} for d in docs]
