import uuid
from datetime import date
from sqlalchemy import UUID, String, ForeignKey, Numeric, Integer, Boolean, Date, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.core.database import Base
from app.models.base import TenantMixin


class RentalUnit(Base, TenantMixin):
    __tablename__ = "rental_units"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=True)  # new, good, fair, poor
    status: Mapped[str] = mapped_column(String(50), default="available")  # available, reserved, on_rent, maintenance, retired
    purchase_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship("Product")


class RentalContract(Base, TenantMixin):
    __tablename__ = "rental_contracts"

    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_sites.id"), nullable=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="booked")  # booked, active, returned, closed, cancelled
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(50), default="monthly")  # monthly, weekly, daily
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    deposit_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, paid, refunded, retained
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    customer: Mapped["Customer"] = relationship("Customer")
    site: Mapped["CustomerSite"] = relationship("CustomerSite")
    company: Mapped["Company"] = relationship("Company")
    lines: Mapped[list["RentalContractLine"]] = relationship("RentalContractLine", back_populates="contract", cascade="all, delete-orphan")


class RentalContractLine(Base, TenantMixin):
    __tablename__ = "rental_contract_lines"

    rental_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rental_contracts.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    rental_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rental_units.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    gst_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=18.0)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    contract: Mapped["RentalContract"] = relationship("RentalContract", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    rental_unit: Mapped["RentalUnit"] = relationship("RentalUnit")


class RentalMovement(Base, TenantMixin):
    __tablename__ = "rental_movements"

    rental_contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rental_contracts.id", ondelete="CASCADE"), nullable=False)
    rental_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rental_units.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # check_out, check_in
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    condition: Mapped[str] = mapped_column(String(100), nullable=True)
    meter_reading: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    charges: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    contract: Mapped["RentalContract"] = relationship("RentalContract")
    rental_unit: Mapped["RentalUnit"] = relationship("RentalUnit")
