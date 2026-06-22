from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token

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

    return CurrentUser(
        user_id=UUID(user_id),
        tenant_id=UUID(tenant_id) if tenant_id else None,
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


def require_platform_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return current_user
