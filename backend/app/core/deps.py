from uuid import UUID
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.core.context import set_actor

bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: UUID, tenant_id: UUID, role: str, is_platform_admin: bool):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.is_platform_admin = is_platform_admin


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

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
