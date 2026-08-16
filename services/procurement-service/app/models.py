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

# Procurement order statuses
PO_DRAFT = "draft"
PO_APPROVED = "approved"
PO_RECEIVED = "received"
PO_CANCELLED = "cancelled"


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
    """A vendor's current quoted price for a branded product (one row per vendor+product).

    `product_id` references the catalog (inventory-service). `material_id`, `brand`, and `product_name`
    are denormalized from the catalog at set-price time so the market view and plans need no runtime
    catalog call."""
    __tablename__ = "vendor_prices"
    __table_args__ = (UniqueConstraint("vendor_id", "product_id", name="uq_vendor_product"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    material_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)  # denormalized
    brand: Mapped[str] = mapped_column(String(80), default="")
    product_name: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    min_qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="prices")


class ExternalOffer(Base):
    """A price observed from an external source (price-scout / supplier price list).

    Advisory market intelligence — NOT part of the deterministic buy plan (the plan buys from the
    registered vendor registry). `confidence` distinguishes `indicative` (LLM/web estimate) from `firm`
    (an uploaded supplier price list). The hub can onboard a promising offer as a registered vendor price.
    """
    __tablename__ = "external_offers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(40), default="")      # llm | stub | csv | serpapi | …
    seller: Mapped[str] = mapped_column(String(160), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    url: Mapped[str] = mapped_column(String(300), default="")
    confidence: Mapped[str] = mapped_column(String(16), default="indicative")  # indicative | firm
    note: Mapped[str] = mapped_column(String(255), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcurementOrder(Base):
    """A hub purchase from vendors. On receive, each line posts an inbound to inventory-service."""
    __tablename__ = "procurement_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(12), default=PO_APPROVED, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["ProcurementLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def code(self) -> str:
        return f"PO-{self.id}"


class ProcurementLine(Base):
    __tablename__ = "procurement_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("procurement_orders.id"), index=True)
    material_id: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), default="")
    product_name: Mapped[str] = mapped_column(String(200), default="")
    vendor_id: Mapped[str] = mapped_column(String(48), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(160), default="")
    qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order: Mapped["ProcurementOrder"] = relationship(back_populates="lines")
