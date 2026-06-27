from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.tenant import Tenant, TenantStatus
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


# Block reasons → 403 messages. Kept as a pure mapping so the decision logic in
# ``tenant_block_reason`` can be unit-tested without DB/HTTP plumbing.
_BLOCK_MESSAGES = {
    "inactive": "This workspace is not active. Contact your administrator.",
    "trial_expired": "Trial period has ended. Contact your administrator.",
}


def tenant_block_reason(status_value: str, is_active: bool,
                        trial_ends_at: Optional[datetime],
                        now: Optional[datetime] = None) -> Optional[str]:
    """Pure decision: why a tenant should be blocked from login/refresh.

    Returns ``"inactive"`` (suspended/cancelled/deactivated), ``"trial_expired"``
    (TRIAL past its window), or ``None`` when the tenant may proceed."""
    if status_value in (TenantStatus.SUSPENDED.value, TenantStatus.CANCELLED.value) or not is_active:
        return "inactive"
    if status_value == TenantStatus.TRIAL.value and trial_ends_at is not None:
        ends = trial_ends_at
        # SQLite (tests) returns naive datetimes; treat them as UTC so the
        # comparison never mixes naive/aware (which raises TypeError).
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        if ends < (now or datetime.now(timezone.utc)):
            return "trial_expired"
    return None


async def _assert_tenant_usable(db: AsyncSession, user: User) -> None:
    """Block login/refresh for tenants that are suspended, cancelled, or past
    their trial window (Phase 1 lifecycle). Platform-admin users manage tenants
    across the platform and are exempt."""
    if user.is_platform_admin or user.tenant_id is None:
        return
    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    reason = tenant_block_reason(tenant.status, tenant.is_active, tenant.trial_ends_at)
    if reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_BLOCK_MESSAGES[reason])


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

    # Block login for suspended/cancelled/expired-trial tenants (Phase 1 lifecycle).
    await _assert_tenant_usable(db, user)

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

    subscription_info = None
    if user.tenant_id:
        from app.models.subscription import TenantSubscription, SaasPlan
        from app.core.deps import get_tenant_active_modules
        sub = (await db.execute(
            select(TenantSubscription, SaasPlan.code)
            .join(SaasPlan, SaasPlan.id == TenantSubscription.plan_id)
            .where(TenantSubscription.tenant_id == user.tenant_id)
            .order_by(TenantSubscription.created_at.desc())
            .limit(1)
        )).first()

        active_mods = await get_tenant_active_modules(db, user.tenant_id)
        if sub:
            tenant_sub, plan_code = sub
            subscription_info = {
                "plan_code": plan_code,
                "status": tenant_sub.status,
                "ends_at": tenant_sub.ends_at.isoformat() if tenant_sub.ends_at else None,
                "active_modules": list(active_mods),
            }
        else:
            subscription_info = {
                "plan_code": "growth",
                "status": "active",
                "ends_at": None,
                "active_modules": list(active_mods),
            }

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "tenant_slug": tenant_slug,
        "totp_enabled": user.totp_enabled,
        "must_change_password": user.must_change_password,
        "permissions": permissions,
        "subscription": subscription_info,
    }


async def change_password(db: AsyncSession, user_id: UUID,
                          current_password: str, new_password: str) -> dict:
    """Set a new password after verifying the current one, clearing the
    forced-reset flag. Used by a provisioned admin to retire its temp password."""
    from app.core.security import hash_password
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New password must be at least 8 characters")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    await db.flush()
    return {"changed": True}


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

    # Stop a suspended/cancelled/expired tenant from minting fresh tokens once the
    # current access token expires (Phase 1 lifecycle).
    await _assert_tenant_usable(db, user)

    # Rotate: revoke the presented token before issuing a new one.
    session.revoked = True
    await db.flush()
    return await _issue_tokens(db, user)
