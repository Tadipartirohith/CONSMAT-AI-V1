"""Margin rules (decision D1: the hub sets the selling price).

A single rule table supports flat, per-tier, per-material, and per-(material,tier) margins at once,
resolved by precedence (Q3). NULL means "any". `material_id`/`tier` reference the catalog (Q11) and the
4-tier consumer classification (D5) as opaque strings.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

CONSUMER_TIERS = ("individual", "contractor", "commercial", "government")


class MarginRule(Base):
    __tablename__ = "margin_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # NULL = any product (brand)
    material_id: Mapped[str | None] = mapped_column(String(40), nullable=True)  # NULL = any material
    tier: Mapped[str | None] = mapped_column(String(20), nullable=True)         # NULL = any tier
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
