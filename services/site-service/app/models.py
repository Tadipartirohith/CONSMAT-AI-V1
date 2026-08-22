"""SQLAlchemy 2.0 models for the field domain: spokes, consumers, sites, plans, phases, dispatches.

A spoke (geo-fenced spokesperson) serves consumers; a consumer owns sites; a site's architect plan
yields a BOM; the civil engineer advances the 9 phases, and completing a phase triggers a Dispatch of
the next phase's materials from hub inventory (hub to site, D3). `material_id` is an opaque reference to
the inventory-service catalog (Q11).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

CONSUMER_TIERS = ("individual", "contractor", "commercial", "government")

# phase progress
PH_PENDING = "pending"
PH_IN_PROGRESS = "in_progress"
PH_DONE = "done"

# dispatch statuses
DSP_DISPATCHED = "dispatched"
DSP_PARTIAL = "partial"
DSP_PENDING = "pending"      # nothing could be fulfilled (stockout to procurement needed)
DSP_RECEIVED = "received"    # customer confirmed receipt

# phase-date change-request statuses (CE edits to a phase end date need spoke/manager approval)
PDC_PENDING = "pending"
PDC_APPROVED = "approved"
PDC_REJECTED = "rejected"

# coverage-area change requests (a spoke's add/remove needs supervisor/manager approval)
AR_PENDING = "pending"
AR_APPROVED = "approved"
AR_REJECTED = "rejected"
AR_ADD = "add"
AR_REMOVE = "remove"


class Spoke(Base):
    __tablename__ = "spokes"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    geofence: Mapped[str] = mapped_column(String(120), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    consumers: Mapped[list["Consumer"]] = relationship(back_populates="spoke")
    areas: Mapped[list["SpokeArea"]] = relationship(back_populates="spoke", cascade="all, delete-orphan")


class SpokeArea(Base):
    """A location keyword the spoke covers (its geofence). A site whose location contains this
    keyword is served by this spoke (Q7)."""
    __tablename__ = "spoke_areas"
    __table_args__ = (UniqueConstraint("spoke_id", "area", name="uq_spoke_area"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    spoke_id: Mapped[str] = mapped_column(ForeignKey("spokes.id"), index=True)
    area: Mapped[str] = mapped_column(String(80), nullable=False)
    spoke: Mapped["Spoke"] = relationship(back_populates="areas")


class AreaRequest(Base):
    """A spoke's request to add/remove a coverage region. Needs supervisor/manager approval; a
    supervisor/manager can also add/remove directly."""
    __tablename__ = "area_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    spoke_id: Mapped[str] = mapped_column(ForeignKey("spokes.id"), index=True)
    area: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(10), default=AR_ADD)   # add | remove
    status: Mapped[str] = mapped_column(String(16), default=AR_PENDING)
    requested_by_role: Mapped[str] = mapped_column(String(32), default="")
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    decided_by_role: Mapped[str] = mapped_column(String(32), default="")
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Consumer(Base):
    __tablename__ = "consumers"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="individual")
    phone: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(160), default="")   # customer login id (identity user)
    # Whether this customer is financed via an NBFC (captured at spoke onboarding, surfaced to admin).
    is_nbfc: Mapped[bool] = mapped_column(Boolean, default=False)
    spoke_id: Mapped[str] = mapped_column(ForeignKey("spokes.id"), index=True)
    spoke: Mapped["Spoke"] = relationship(back_populates="consumers")
    sites: Mapped[list["Site"]] = relationship(back_populates="consumer")


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    consumer_id: Mapped[str] = mapped_column(ForeignKey("consumers.id"), index=True)
    label: Mapped[str] = mapped_column(String(160), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    area_sqft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    floors: Mapped[int] = mapped_column(Integer, default=1)
    construction_type: Mapped[str] = mapped_column(String(20), default="standard")
    status: Mapped[str] = mapped_column(String(16), default="planning")  # planning|planned|active|completed
    total_area: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    consumer: Mapped["Consumer"] = relationship(back_populates="sites")
    bom_lines: Mapped[list["BOMLine"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    phases: Mapped[list["PhaseProgress"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="site", cascade="all, delete-orphan")

    @property
    def code(self) -> str:
        return f"SITE-{self.id}"


class Phase(Base):
    """Reference table of the 9 construction phases (seeded)."""
    __tablename__ = "phases"
    seq: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    repeats_per_floor: Mapped[bool] = mapped_column(Boolean, default=False)


class BOMLine(Base):
    __tablename__ = "bom_lines"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    material_id: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), default="")     # brand SKU when CE/spoke enters it
    product_name: Mapped[str] = mapped_column(String(200), default="")
    phase_seq: Mapped[int] = mapped_column(Integer, default=0)  # 0 = whole-project (auto-slice); 1-9 = explicit phase
    total_qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    site: Mapped["Site"] = relationship(back_populates="bom_lines")


class PhaseProgress(Base):
    __tablename__ = "phase_progress"
    __table_args__ = (UniqueConstraint("site_id", "phase_seq", name="uq_site_phase"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PH_PENDING)
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispatched: Mapped[bool] = mapped_column(Boolean, default=False)  # next-phase JIT dispatch already done
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site: Mapped["Site"] = relationship(back_populates="phases")


class PhaseDateChange(Base):
    """A requested change to a phase's planned end date.

    A civil engineer's edit lands here as `pending` and must be approved by the spoke or the hub
    manager; a spoke/manager edit is applied directly and recorded here as `approved`.
    """
    __tablename__ = "phase_date_changes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    old_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PDC_PENDING)
    requested_by_role: Mapped[str] = mapped_column(String(32), default="")
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    decided_by_role: Mapped[str] = mapped_column(String(32), default="")
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    """A message to the field team (civil engineer / spokesperson) about a site.

    Written by the JIT scheduler: 3 days before a phase's end it warns that next-phase stock is about
    to dispatch, and again when the stock is dispatched, so work is never halted for want of material.
    """
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    spoke_id: Mapped[str] = mapped_column(String(48), default="", index=True)
    audience: Mapped[str] = mapped_column(String(24), default="field")  # field|civil_engineer|spokesperson
    phase_seq: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(32), default="")  # dispatch_pending|dispatched|low_stock
    message: Mapped[str] = mapped_column(String(300), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dispatch(Base):
    __tablename__ = "dispatches"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=DSP_DISPATCHED)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    site: Mapped["Site"] = relationship(back_populates="dispatches")
    lines: Mapped[list["DispatchLine"]] = relationship(back_populates="dispatch", cascade="all, delete-orphan")

    @property
    def code(self) -> str:
        return f"DSP-{self.id}"


class DispatchLine(Base):
    __tablename__ = "dispatch_lines"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), index=True)
    material_id: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), default="")
    product_name: Mapped[str] = mapped_column(String(200), default="")
    qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=DSP_DISPATCHED)  # dispatched|short
    dispatch: Mapped["Dispatch"] = relationship(back_populates="lines")
