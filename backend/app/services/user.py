from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User, TenantRole
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

    # Enforce subscription plan limits (SRS 4.1). Technicians count against both
    # the overall user cap and the separate technician cap.
    from app.services.tenant import enforce_limit
    await enforce_limit(db, tenant_id, "users")
    if payload.role == TenantRole.TECHNICIAN:
        await enforce_limit(db, tenant_id, "technicians")

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


async def list_users_for_tenant(db: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 200) -> list[User]:
    """Platform-admin helper: list all users belonging to any tenant (no RLS isolation)."""
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def admin_reset_password(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> tuple[User, str]:
    """Platform-admin: force-reset a tenant user's password.

    Generates a cryptographically-secure temporary password, stores its hash,
    and flags the account so the user is prompted to change it on next login.
    Returns (user, plaintext_temp_password) — the plaintext is shown once only.
    """
    import secrets
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in this tenant")

    temp_password = secrets.token_urlsafe(12)
    user.hashed_password = hash_password(temp_password)
    user.must_change_password = True
    await db.commit()
    await db.refresh(user)
    return user, temp_password
