from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.core.security import hash_password
from app.repositories.base import TenantRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(TenantRepository[User]):
    model = User


async def list_users(db, tenant_id, offset=0, limit=50):
    return await UserRepository(db, tenant_id).list(offset=offset, limit=limit)


async def get_user(db, tenant_id, user_id):
    obj = await UserRepository(db, tenant_id).get(user_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return obj


async def create_user(db: AsyncSession, tenant_id: UUID, payload: UserCreate) -> User:
    # Check email uniqueness within tenant
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == payload.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    return await UserRepository(db, tenant_id).create(user)


async def update_user(db, tenant_id, user_id, payload: UserUpdate) -> User:
    repo = UserRepository(db, tenant_id)
    obj = await repo.get(user_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    return await repo.save(obj)
