"""SQLAlchemy 2.0 models for the vendor registry + price lists.

The hub keeps a list of vendors and their pricing (decision D1) and can add new vendors at any time.
`Vendor.is_hub_self=True` models the hub's own supply as a vendor, so procurement selection can treat
the hub uniformly alongside external suppliers. `material_id` is an opaque reference to the catalog
owned by inventory-service (Q11) — no cross-service foreign key.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    gstin: Mapped[str] = mapped_column(String(24), default="")
    is_hub_self: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prices: Mapped[list["VendorPrice"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorPrice(Base):
    """A vendor's current quoted price for a material (one row per vendor+material)."""
    __tablename__ = "vendor_prices"
    __table_args__ = (UniqueConstraint("vendor_id", "material_id", name="uq_vendor_material"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True, nullable=False)
    material_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    min_qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="prices")
