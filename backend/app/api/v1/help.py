from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_tenant_active_modules
from app.services import help as help_service

router = APIRouter()

class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Article rating from 1 to 5 stars")
    comments: str = Field(None, description="Optional textual comment or suggestions")
    is_outdated: bool = Field(False, description="Flag indicating if the document needs revision")


@router.get("/menu")
async def get_help_menu(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get the documentation menu category hierarchy tree, filtered by the tenant's subscribed modules
    and the user's role permission matrices.
    """
    active_modules = []
    if current_user.tenant_id:
        modules_set = await get_tenant_active_modules(db, current_user.tenant_id)
        active_modules = list(modules_set)

    return await help_service.get_help_menu(
        db=db,
        active_modules=active_modules,
        user_role=current_user.role,
        is_platform_admin=current_user.is_platform_admin
    )


@router.get("/articles/{slug}")
async def get_help_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get dynamic help article content details including prerequisites, content body, attachments,
    and nested FAQs. Enforces module-aware and role-based permissions.
    """
    active_modules = []
    if current_user.tenant_id:
        modules_set = await get_tenant_active_modules(db, current_user.tenant_id)
        active_modules = list(modules_set)

    return await help_service.get_help_article(
        db=db,
        slug=slug,
        active_modules=active_modules,
        user_role=current_user.role,
        is_platform_admin=current_user.is_platform_admin
    )


@router.get("/search")
async def search_help_articles(
    q: str = Query(..., min_length=2, description="The search term"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Global search within documentation articles, metadata, titles, and FAQs.
    Automatically filters and returns highlighted search snippets.
    """
    active_modules = []
    if current_user.tenant_id:
        modules_set = await get_tenant_active_modules(db, current_user.tenant_id)
        active_modules = list(modules_set)

    return await help_service.search_help_articles(
        db=db,
        query=q,
        active_modules=active_modules,
        user_role=current_user.role,
        is_platform_admin=current_user.is_platform_admin
    )


@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    article_id: UUID,
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Submit rating or report outdated content for a help article."""
    return await help_service.create_feedback(
        db=db,
        article_id=article_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        rating=payload.rating,
        comments=payload.comments,
        is_outdated=payload.is_outdated
    )


@router.post("/articles/{article_id}/bookmark")
async def toggle_bookmark(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Toggle a documentation bookmark (adds if absent, removes if present)."""
    is_bookmarked = await help_service.toggle_bookmark(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        article_id=article_id
    )
    return {"bookmarked": is_bookmarked}


@router.get("/bookmarks")
async def list_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Lists all the help articles bookmarked by the current user."""
    return await help_service.get_bookmarked_articles(
        db=db,
        user_id=current_user.user_id
    )


@router.get("/attachments/{attachment_id}/download")
async def download_help_attachment(
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.models.help import HelpAttachment
    from app.services import storage
    from app.core.config import get_settings
    from fastapi.responses import StreamingResponse
    from sqlalchemy import select
    import io

    result = await db.execute(
        select(HelpAttachment).where(HelpAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    settings = get_settings()
    bucket = settings.S3_BUCKET
    url_parts = attachment.url.split(f"/{bucket}/")
    if len(url_parts) < 2:
        # Fallback to absolute url if not stored in default bucket structure
        key = attachment.url.split("/")[-1]
    else:
        key = url_parts[1]

    content, content_type = storage.download_bytes(key)
    if content is None:
        raise HTTPException(status_code=404, detail="File content not found in storage")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{attachment.file_name}"'}
    )
