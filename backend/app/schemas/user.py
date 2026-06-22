from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import TenantRole


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str
    role: TenantRole = TenantRole.VIEWER


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[TenantRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    phone: Optional[str]
    role: str
    is_active: bool
