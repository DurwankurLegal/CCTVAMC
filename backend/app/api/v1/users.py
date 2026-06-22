from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_roles
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services import user as user_service

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    return await user_service.list_users(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    return await user_service.create_user(db, current_user.tenant_id, payload)


@router.get("/me", response_model=UserResponse)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await user_service.get_user(db, current_user.tenant_id, current_user.user_id)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    return await user_service.get_user(db, current_user.tenant_id, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("admin")),
):
    return await user_service.update_user(db, current_user.tenant_id, user_id, payload)
