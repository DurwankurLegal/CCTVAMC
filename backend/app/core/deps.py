from typing import Optional
from uuid import UUID
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.core.context import set_actor

# auto_error=False so a *missing* Authorization header yields 401 (handled
# below) rather than HTTPBearer's default 403 — 401 is the correct status for
# "no credentials supplied" and lets clients trigger re-login.
bearer_scheme = HTTPBearer(auto_error=False)


def _require_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> HTTPAuthorizationCredentials:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials


class CurrentUser:
    def __init__(self, user_id: UUID, tenant_id: UUID, role: str, is_platform_admin: bool):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.is_platform_admin = is_platform_admin


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    credentials = _require_credentials(credentials)
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # Portal-scoped tokens must never reach staff/back-office APIs.
    if payload.get("scope") == "portal":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for staff APIs")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "viewer")
    is_platform_admin = payload.get("is_platform_admin", False)

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = UUID(user_id)
    tid = UUID(tenant_id) if tenant_id else None
    # Make actor available to audit/RLS and bind to structured logs for this request.
    set_actor(uid, tid)
    structlog.contextvars.bind_contextvars(
        user_id=str(uid), tenant_id=str(tid) if tid else None
    )

    return CurrentUser(
        user_id=uid,
        tenant_id=tid,
        role=role,
        is_platform_admin=is_platform_admin,
    )


def require_roles(*roles: str):
    async def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_platform_admin:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker


async def get_effective_permissions(db: AsyncSession, current_user: "CurrentUser") -> set:
    """Resolve a user's effective permission codes.

    If the user has explicit DB role assignments (custom RBAC), the union of
    those roles' permissions is authoritative; otherwise fall back to the
    code-defined default matrix keyed off the legacy ``role`` string.
    """
    from sqlalchemy import select
    from app.models.rbac import UserRole, RolePermission, Permission
    from app.core.permissions import default_permissions_for_role

    rows = (await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == current_user.user_id)
    )).scalars().all()
    if rows:
        return set(rows)
    return default_permissions_for_role(current_user.role)


def require_permission(code: str):
    async def checker(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        if current_user.is_platform_admin:
            return current_user
        perms = await get_effective_permissions(db, current_user)
        if code not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {code}",
            )
        return current_user
    return checker


def require_platform_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return current_user


class PortalUser:
    """Authenticated customer self-service portal user. Carries the customer_id
    that scopes every portal query in addition to tenant_id."""
    def __init__(self, user_id: UUID, tenant_id: UUID, customer_id: UUID):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.customer_id = customer_id


async def get_current_portal_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> PortalUser:
    """Validate a portal-scoped token. Rejects staff tokens (no portal scope)."""
    credentials = _require_credentials(credentials)
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access" or payload.get("scope") != "portal":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid portal token")
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    customer_id = payload.get("customer_id")
    if not user_id or not tenant_id or not customer_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid portal token")
    uid, tid, cid = UUID(user_id), UUID(tenant_id), UUID(customer_id)
    # Bind actor + tenant for audit/RLS and structured logging.
    set_actor(uid, tid)
    structlog.contextvars.bind_contextvars(
        portal_user_id=str(uid), tenant_id=str(tid), customer_id=str(cid)
    )
    return PortalUser(user_id=uid, tenant_id=tid, customer_id=cid)


async def get_tenant_active_modules(db: AsyncSession, tenant_id: UUID) -> set[str]:
    """Fetch active module codes for a tenant, utilizing Redis cache."""
    import redis.asyncio as aioredis
    from sqlalchemy import select
    from app.core.config import get_settings
    from app.models.subscription import TenantModule

    settings = get_settings()
    redis_client = aioredis.from_url(settings.REDIS_URL)
    cache_key = f"tenant:{tenant_id}:modules"

    try:
        cached_modules = await redis_client.smembers(cache_key)
        if cached_modules:
            return {m.decode("utf-8") for m in cached_modules}
    except Exception:
        pass

    # Database Query
    stmt = select(TenantModule.module_code).where(
        TenantModule.tenant_id == tenant_id,
        TenantModule.status == "active"
    )
    result = await db.execute(stmt)
    modules = set(result.scalars().all())

    # Self-healing fallback for legacy or test-created tenants without module config seeded
    if not modules:
        from sqlalchemy import func
        stmt_count = select(func.count(TenantModule.id)).where(TenantModule.tenant_id == tenant_id)
        has_any_config = (await db.execute(stmt_count)).scalar() or 0
        if has_any_config == 0:
            from app.models.subscription import TenantSubscription
            stmt_sub = select(func.count(TenantSubscription.id)).where(TenantSubscription.tenant_id == tenant_id)
            has_sub = (await db.execute(stmt_sub)).scalar() or 0
            if has_sub > 0:
                # Provisioned tenant with explicit empty configuration
                return set()
            
            from app.models.subscription import Module
            stmt_all = select(Module.code).where(Module.is_active == True)
            all_modules = set((await db.execute(stmt_all)).scalars().all())
            if not all_modules:
                return {"sales", "rental", "amc", "inventory", "assets"}
            modules = all_modules

    try:
        if modules:
            await redis_client.sadd(cache_key, *modules)
            await redis_client.expire(cache_key, 3600)
    except Exception:
        pass

    return modules


def require_module(module_code: str):
    """Router dependency to assert the active tenant has subscribed to the specified module."""
    async def checker(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> CurrentUser:
        if current_user.is_platform_admin:
            return current_user

        # Core modules always allowed
        if module_code in ("dashboard", "customers", "users", "tenants"):
            return current_user

        active_modules = await get_tenant_active_modules(db, current_user.tenant_id)
        if module_code not in active_modules:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription upgrade required. The '{module_code}' module is disabled."
            )
        return current_user
    return checker


def require_module_any(module_codes: list[str]):
    """Router dependency to assert the active tenant has subscribed to at least one of the specified modules."""
    async def checker(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> CurrentUser:
        if current_user.is_platform_admin:
            return current_user

        active_modules = await get_tenant_active_modules(db, current_user.tenant_id)
        if not any(m in active_modules for m in module_codes):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription upgrade required. At least one of {module_codes} modules must be active."
            )
        return current_user
    return checker

