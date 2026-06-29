from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.services import document as document_service
from app.services import storage

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
    return {"id": str(doc.id), "url": f"/api/v1/documents/{doc.id}/view", "s3_key": doc.s3_key}


@router.get("")
async def list_documents(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    docs = await document_service.list_documents(db, current_user.tenant_id, entity_type, entity_id)
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "url": f"/api/v1/documents/{d.id}/view"
        }
        for d in docs
    ]


@router.get("/{document_id}/view")
async def view_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    doc = await document_service.get_document(db, current_user.tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    content, content_type = storage.download_bytes(doc.s3_key)
    if content is None:
        raise HTTPException(status_code=404, detail="File content not found in storage")
        
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'}
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("documents:write")),
):
    await document_service.delete_document(db, current_user.tenant_id, document_id)
    return Response(status_code=204)
