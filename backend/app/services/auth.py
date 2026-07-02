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
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, SignUpRequest
from app.schemas.tenant import TenantCreate
from app.schemas.user import UserCreate
from app.services.tenant import create_tenant
from app.services.user import create_user
from app.models.user import TenantRole

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

    # Optional second factor (TOTP) — SRS 4.21.
    if user.totp_enabled:
        import pyotp
        code = getattr(payload, "otp_code", None)
        if not code or not pyotp.TOTP(user.totp_secret).verify(str(code), valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing 2FA code")

    return await _issue_tokens(db, user)


async def current_user_info(db: AsyncSession, user_id: UUID) -> dict:
    """Return the authenticated user's identity for the frontend (route guards,
    profile). Tenant slug is included so the UI can show the active tenant."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    tenant_slug = None
    if user.tenant_id:
        tenant_slug = (await db.execute(
            select(Tenant.slug).where(Tenant.id == user.tenant_id))).scalar_one_or_none()

    # Effective permissions drive permission-aware menu/route visibility in the UI.
    from app.core.deps import get_effective_permissions
    from app.core.permissions import ALL_PERMISSIONS

    class _Principal:
        user_id = user.id
        role = user.role
    if user.is_platform_admin:
        permissions = sorted(ALL_PERMISSIONS)
    else:
        permissions = sorted(await get_effective_permissions(db, _Principal()))

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "tenant_slug": tenant_slug,
        "totp_enabled": user.totp_enabled,
        "permissions": permissions,
    }


async def enroll_2fa(db: AsyncSession, user_id: UUID, issuer: str = "CCTV AMC") -> dict:
    """Generate a TOTP secret + provisioning URI for an authenticator app."""
    import pyotp
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled = False  # not active until first verify
    await db.flush()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    return {"secret": secret, "provisioning_uri": uri}


async def verify_2fa(db: AsyncSession, user_id: UUID, code: str) -> dict:
    """Verify the first TOTP code and enable 2FA for the account."""
    import pyotp
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enroll 2FA first")
    if not pyotp.TOTP(user.totp_secret).verify(str(code), valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
    user.totp_enabled = True
    await db.flush()
    return {"enabled": True}


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


async def signup(db: AsyncSession, payload: SignUpRequest) -> TokenResponse:
    # 1. Create a new tenant
    tenant_payload = TenantCreate(
        name=payload.company_name,
        slug=payload.company_slug,
    )
    # This will check slug uniqueness and raise HTTP 409 if taken.
    tenant = await create_tenant(db, tenant_payload)

    # 2. Create the admin user for the tenant
    user_payload = UserCreate(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        role=TenantRole.ADMIN,
    )
    user = await create_user(db, tenant.id, user_payload)

    # 3. Issue tokens and log them in
    return await _issue_tokens(db, user)
