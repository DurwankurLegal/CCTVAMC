from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.models.notification import NotificationTemplate, NotificationLog

router = APIRouter()


class TemplateCreate(BaseModel):
    event_type: str
    channel: str
    subject: Optional[str] = None
    body: str


class TemplateResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    event_type: str
    channel: str
    subject: Optional[str]
    body: str
    is_active: bool


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    result = await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.tenant_id == current_user.tenant_id)
    )
    return list(result.scalars().all())


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    payload: TemplateCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    tmpl = NotificationTemplate(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(tmpl)
    await db.flush()
    await db.refresh(tmpl)
    return tmpl


@router.get("/logs")
async def list_logs(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == current_user.tenant_id)
        .offset(offset).limit(limit)
    )
    return list(result.scalars().all())
