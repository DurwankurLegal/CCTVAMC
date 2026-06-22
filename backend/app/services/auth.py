from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest


async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
    }
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


async def refresh(db: AsyncSession, payload: RefreshRequest) -> TokenResponse:
    claims = decode_token(payload.refresh_token)
    if not claims or claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == UUID(claims["sub"]), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
    }
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
