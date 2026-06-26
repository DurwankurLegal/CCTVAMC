from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.company_template import CompanyTemplateCreate, CompanyTemplateUpdate, CompanyTemplateResponse
from app.models.company_template import CompanyTemplate
from app.services import company_template as template_service

router = APIRouter()

@router.get("", response_model=List[CompanyTemplateResponse])
async def list_company_templates(
    company_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = template_service.CompanyTemplateRepository(db, current_user.tenant_id)
    await repo._set_rls_context()
    stmt = select(CompanyTemplate).where(
        CompanyTemplate.tenant_id == current_user.tenant_id,
        CompanyTemplate.company_id == company_id
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())

@router.post("", response_model=CompanyTemplateResponse)
async def upsert_company_template(
    payload: CompanyTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("tenants:write")),
):
    # Upsert logic: if template for company_id + document_type already exists, update it. Otherwise create it.
    existing = await template_service.get_template_by_type(
        db, current_user.tenant_id, payload.company_id, payload.document_type
    )
    if existing:
        return await template_service.update_template(
            db, current_user.tenant_id, existing.id,
            CompanyTemplateUpdate(
                template_html=payload.template_html,
                header_html=payload.header_html,
                footer_html=payload.footer_html,
                is_active=payload.is_active
            )
        )
    return await template_service.create_template(db, current_user.tenant_id, payload)

@router.get("/{template_id}", response_model=CompanyTemplateResponse)
async def get_company_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await template_service.get_template(db, current_user.tenant_id, template_id)
