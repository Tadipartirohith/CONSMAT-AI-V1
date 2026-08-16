"""SQLAlchemy 2.0 models for the hub inventory + append-only ledger.

Ownership (D3): the hub is the sole inventory location. `InventoryItem` holds the current
position per material; `LedgerEntry` is the immutable audit trail of every movement. `on_hand`
is the running sum of ledger movements and can be recomputed for reconciliation.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Movement directions
INBOUND = "inbound"        # procurement receipt / hub own supply
OUTBOUND = "outbound"      # dispatch to a site
ADJUSTMENT = "adjustment"  # correction / wastage (signed)

# Reference types (what caused the movement)
REF_PROCUREMENT = "procurement"
REF_DISPATCH = "dispatch"
REF_ADJUSTMENT = "adjustment"
REF_SEED = "seed"


class Material(Base):
    """Reference catalog entry. Provisionally owned here (see Q11) until a catalog service exists."""
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="")
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    grade: Mapped[str] = mapped_column(String(60), default="")
    per_sqft: Mapped[Decimal] = mapped_column(Numeric(12, 5), default=Decimal("0"))

    item: Mapped["InventoryItem"] = relationship(back_populates="material", uselist=False)


class InventoryItem(Base):
    """Current stock position for a material at the hub."""
    __tablename__ = "inventory_items"

    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"), primary_key=True)
    on_hand: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=Decimal("0"), nullable=False)
    reserved: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=Decimal("0"), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    material: Mapped["Material"] = relationship(back_populates="item")

    @property
    def available(self) -> Decimal:
        return self.on_hand - self.reserved


class LedgerEntry(Base):
    """Immutable record of a single stock movement (append-only)."""
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(12), nullable=False)  # inbound|outbound|adjustment
    qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)  # signed (+in / -out)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(24), default=REF_ADJUSTMENT)
    ref_id: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(String(255), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
