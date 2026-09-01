"""Payment records."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# statuses
PENDING = "pending"
PAID = "paid"
FAILED = "failed"
REFUNDED = "refunded"
# Escrow: funds are captured from the payer but HELD, and only RELEASED to the supplier as deliveries
# are confirmed at the site (partial holds move released_amount up until it equals amount -> released).
HELD = "held"
RELEASED = "released"

# Invoice (client progress billing) statuses - PDF stage 13
INV_DRAFT = "draft"
INV_ISSUED = "issued"
INV_PAID = "paid"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ref: Mapped[str] = mapped_column(String(64), index=True, default="")   # e.g. SITE-1 / quote id
    consumer_id: Mapped[str] = mapped_column(String(64), index=True, default="")  # payer
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    released_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    provider: Mapped[str] = mapped_column(String(24), default="mock")
    provider_ref: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(16), default=PENDING)
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def code(self) -> str:
        return f"PAY-{self.id}"


class Invoice(Base):
    """A client-facing progress bill for a project (a phase milestone or a lump amount). Issued by the
    hub/spoke, paid by the consumer. PDF stage 13 (billing) on the client side."""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ref: Mapped[str] = mapped_column(String(64), index=True, default="")   # SITE-<id>
    consumer_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    phase_seq: Mapped[int] = mapped_column(Integer, default=0)             # 0 = lump / not phase-tied
    title: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(12), default=INV_ISSUED)
    note: Mapped[str] = mapped_column(String(255), default="")
    payment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def code(self) -> str:
        return f"INV-{self.id}"
