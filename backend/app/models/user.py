import uuid
from enum import Enum
from sqlalchemy import UUID, String, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base
from app.models.base import TenantMixin


class TenantRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


class User(Base, TenantMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=TenantRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
