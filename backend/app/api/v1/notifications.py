from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
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
    current_user: CurrentUser = Depends(require_permission("notifications:write")),
):
    result = await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.tenant_id == current_user.tenant_id)
    )
    return list(result.scalars().all())


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    payload: TemplateCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("notifications:write")),
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
    current_user: CurrentUser = Depends(require_permission("notifications:write")),
):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == current_user.tenant_id)
        .offset(offset).limit(limit)
    )
    return list(result.scalars().all())


# ── In-app notification center (current user) ─────────────────
@router.get("")
async def my_notifications(
    unread_only: bool = Query(False),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.models.notification import NotificationChannel
    stmt = select(NotificationLog).where(
        NotificationLog.tenant_id == current_user.tenant_id,
        NotificationLog.recipient_user_id == current_user.user_id,
        NotificationLog.channel == NotificationChannel.IN_APP,
    )
    if unread_only:
        stmt = stmt.where(NotificationLog.read_at.is_(None))
    stmt = stmt.order_by(NotificationLog.created_at.desc()).offset(offset).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from datetime import datetime, timezone
    from fastapi import HTTPException
    log = (await db.execute(
        select(NotificationLog).where(
            NotificationLog.id == notification_id,
            NotificationLog.tenant_id == current_user.tenant_id,
            NotificationLog.recipient_user_id == current_user.user_id,
        )
    )).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Notification not found")
    log.read_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "read", "id": str(notification_id)}
