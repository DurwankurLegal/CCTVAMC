import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Integer, Numeric, DateTime, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin

class Module(Base, TimestampMixin):
    """Registry of functional modules available in the SaaS platform."""
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Feature(Base, TimestampMixin):
    """Granular features inside a module (e.g. 'amc:preventive_maintenance')."""
    __tablename__ = "features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)


class ModuleDependency(Base, TimestampMixin):
    """Declares hard dependencies between modules (e.g., rental -> assets)."""
    __tablename__ = "module_dependencies"
    __table_args__ = (
        UniqueConstraint("module_code", "depends_on_code", name="uq_module_dependency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    depends_on_code: Mapped[str] = mapped_column(String(50), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(50), default="MANDATORY") # MANDATORY, OPTIONAL


class SaasPlan(Base, TimestampMixin):
    """SaaS plans mapping, replacing the old static hardcoded strings."""
    __tablename__ = "saas_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_monthly: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    max_users: Mapped[int] = mapped_column(Integer, default=0)
    max_sites: Mapped[int] = mapped_column(Integer, default=0)
    max_technicians: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PlanModule(Base, TimestampMixin):
    """Maps default modules included in a SaaS plan."""
    __tablename__ = "plan_modules"
    __table_args__ = (
        UniqueConstraint("plan_id", "module_code", name="uq_plan_module"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("saas_plans.id", ondelete="CASCADE"), nullable=False)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False)


class TenantSubscription(Base, TimestampMixin):
    """Stores the active subscription details of a tenant."""
    __tablename__ = "tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("saas_plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantModule(Base, TimestampMixin):
    """Individual modules enabled for a specific tenant. Overrides/customizes plan defaults."""
    __tablename__ = "tenant_modules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module_code", name="uq_tenant_module"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantFeature(Base, TimestampMixin):
    """Toggles specific features for individual tenants."""
    __tablename__ = "tenant_features"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_code", name="uq_tenant_feature"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_code: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SubscriptionHistory(Base, TimestampMixin):
    """Audit log tracking all upgrades, downgrades, and cancellations."""
    __tablename__ = "subscription_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    performed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)


class UsageStatistics(Base, TimestampMixin):
    """Accumulates tenant usage metrics to verify limits and meter consumption."""
    __tablename__ = "usage_statistics"
    __table_args__ = (
        UniqueConstraint("tenant_id", "metric_name", name="uq_tenant_usage_metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
