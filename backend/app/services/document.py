from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import TenantRepository
from app.services import storage


class DocumentRepository(TenantRepository[Document]):
    model = Document


async def upload_document(
    db: AsyncSession, tenant_id: UUID, *, entity_type: str, entity_id: UUID,
    doc_type: str, file_name: str, content: bytes, content_type: str | None,
    uploaded_by: UUID | None = None, notes: str | None = None,
) -> Document:
    key = storage.build_key(tenant_id, entity_type, file_name)
    url = storage.upload_bytes(key, content, content_type)
    doc = Document(
        entity_type=entity_type, entity_id=entity_id, doc_type=doc_type,
        file_name=file_name, content_type=content_type, s3_key=key, url=url,
        uploaded_by=uploaded_by, notes=notes,
    )
    return await DocumentRepository(db, tenant_id).create(doc)


async def list_documents(db: AsyncSession, tenant_id: UUID, entity_type: str, entity_id: UUID):
    result = await db.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.entity_type == entity_type,
            Document.entity_id == entity_id,
        )
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document | None:
    return await DocumentRepository(db, tenant_id).get(document_id)


async def delete_document(db: AsyncSession, tenant_id: UUID, document_id: UUID) -> None:
    from fastapi import HTTPException, status
    repo = DocumentRepository(db, tenant_id)
    doc = await repo.get(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.s3_key:
        storage.delete_file(doc.s3_key)
    await repo.delete(document_id)
