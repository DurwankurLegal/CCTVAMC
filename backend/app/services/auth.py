from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.tenant import Tenant
from app.models.auth_session import AuthSession
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, decode_token,
)
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest


def _token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
    }


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    data = _token_payload(user)
    access = create_access_token(data)
    refresh, jti, expires_at = create_refresh_token(data)
    db.add(AuthSession(
        user_id=user.id, tenant_id=user.tenant_id, jti=jti, expires_at=expires_at,
    ))
    await db.flush()
    return TokenResponse(access_token=access, refresh_token=refresh)


async def _resolve_tenant_id(db: AsyncSession, tenant_slug: Optional[str]) -> Optional[UUID]:
    if not tenant_slug:
        return None
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tid = result.scalar_one_or_none()
    if not tid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return tid


async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    # Tenant-scope the lookup when a slug is supplied; otherwise match by email.
    # Emails are unique per tenant, so the same email may exist in two tenants —
    # selecting all matches avoids MultipleResultsFound and lets us disambiguate.
    tenant_id = await _resolve_tenant_id(db, getattr(payload, "tenant_slug", None))
    stmt = select(User).where(User.email == payload.email, User.is_active == True)
    if tenant_id is not None:
        stmt = stmt.where(User.tenant_id == tenant_id)
    candidates = (await db.execute(stmt)).scalars().all()

    if len(candidates) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email exists in multiple tenants; specify tenant_slug",
        )
    user = candidates[0] if candidates else None
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return await _issue_tokens(db, user)


async def refresh(db: AsyncSession, payload: RefreshRequest) -> TokenResponse:
    claims = decode_token(payload.refresh_token)
    if not claims or claims.get("type") != "refresh" or not claims.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    session = (await db.execute(
        select(AuthSession).where(AuthSession.jti == claims["jti"])
    )).scalar_one_or_none()
    if not session or session.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    user = (await db.execute(
        select(User).where(User.id == UUID(claims["sub"]), User.is_active == True)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate: revoke the presented token before issuing a new one.
    session.revoked = True
    await db.flush()
    return await _issue_tokens(db, user)
