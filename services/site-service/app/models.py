"""SQLAlchemy 2.0 models for the field domain: spokes, consumers, sites, plans, phases, dispatches.

A spoke (geo-fenced spokesperson) serves consumers; a consumer owns sites; a site's architect plan
yields a BOM; the civil engineer advances the 9 phases, and completing a phase triggers a Dispatch of
the next phase's materials from hub inventory (hub → site, D3). `material_id` is an opaque reference to
the inventory-service catalog (Q11).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
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
DSP_PENDING = "pending"      # nothing could be fulfilled (stockout → procurement needed)


class Spoke(Base):
    __tablename__ = "spokes"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    geofence: Mapped[str] = mapped_column(String(120), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    consumers: Mapped[list["Consumer"]] = relationship(back_populates="spoke")


class Consumer(Base):
    __tablename__ = "consumers"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="individual")
    phone: Mapped[str] = mapped_column(String(32), default="")
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
    total_qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    site: Mapped["Site"] = relationship(back_populates="bom_lines")


class PhaseProgress(Base):
    __tablename__ = "phase_progress"
    __table_args__ = (UniqueConstraint("site_id", "phase_seq", name="uq_site_phase"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PH_PENDING)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site: Mapped["Site"] = relationship(back_populates="phases")


class Dispatch(Base):
    __tablename__ = "dispatches"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=DSP_DISPATCHED)
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
    qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=DSP_DISPATCHED)  # dispatched|short
    dispatch: Mapped["Dispatch"] = relationship(back_populates="lines")
