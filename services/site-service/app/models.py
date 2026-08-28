"""SQLAlchemy 2.0 models for the field domain: spokes, consumers, sites, plans, phases, dispatches.

A spoke (geo-fenced spokesperson) serves consumers; a consumer owns sites; a site's architect plan
yields a BOM; the site engineer advances the 9 phases, and completing a phase triggers a Dispatch of
the next phase's materials from hub inventory (hub to site, D3). `material_id` is an opaque reference to
the inventory-service catalog (Q11).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String,
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

# phase-date change-request statuses (SE edits to a phase end date need spoke/manager approval)
PDC_PENDING = "pending"
PDC_APPROVED = "approved"
PDC_REJECTED = "rejected"

# coverage-area change requests (a spoke's add/remove needs supervisor/manager approval)
AR_PENDING = "pending"
AR_APPROVED = "approved"
AR_REJECTED = "rejected"
AR_ADD = "add"
AR_REMOVE = "remove"

# project financing type (chosen per project at/after onboarding; replaces the old consumer NBFC flag)
PROJECT_TYPES = ("captive", "client")

# BOQ sources + statuses (SE BOQ vs an external app's BOQ, reconciled into a final BOQ that is approved)
BOQ_CE = "ce"
BOQ_EXTERNAL = "external"
BOQ_FINAL = "final"
BOQ_DRAFT = "draft"
BOQ_SUBMITTED = "submitted"
BOQ_APPROVED = "approved"
BOQ_REJECTED = "rejected"
BOQ_SUPERSEDED = "superseded"
BOQ_DIFF_THRESHOLD = 5.0  # % resource difference above which a reconciled final BOQ is required

# Project finance (the spoke's internal finance team secures funding from a preferred partner)
FIN_PENDING = "pending"
FIN_IN_PROGRESS = "in_progress"
FIN_APPROVED = "approved"
FIN_REJECTED = "rejected"
FINANCE_STATUSES = (FIN_PENDING, FIN_IN_PROGRESS, FIN_APPROVED, FIN_REJECTED)

# project lifecycle stage (pre-delivery gate; distinct from the construction `status`)
STAGE_ONBOARDED = "onboarded"
STAGE_DESIGN = "design_uploaded"
STAGE_BOQ_REVIEW = "boq_review"
STAGE_BOQ_APPROVED = "boq_approved"
STAGE_BUDGETED = "budgeted"
STAGE_FINANCING = "financing"
STAGE_FINANCE_APPROVED = "finance_approved"
STAGE_AWAITING_PAYMENT = "awaiting_payment"
STAGE_PAID = "paid"
STAGE_SCHEDULING = "scheduling"
STAGE_ACTIVE = "active"
STAGE_COMPLETED = "completed"


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
    # Financing type + pre-delivery lifecycle (drives the delivery trigger: captive=finance, client=payment).
    project_type: Mapped[str] = mapped_column(String(12), default="")  # captive | client
    stage: Mapped[str] = mapped_column(String(24), default=STAGE_ONBOARDED)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)  # hub-issued
    payment_received: Mapped[bool] = mapped_column(Boolean, default=False)  # client-project delivery gate
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
    product_id: Mapped[str] = mapped_column(String(64), default="")     # brand SKU when SE/spoke enters it
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

    A site engineer's edit lands here as `pending` and must be approved by the spoke or the hub
    manager; a spoke/manager edit is applied directly and recorded here as `approved`.
    """
    __tablename__ = "phase_date_changes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    phase_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    old_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PDC_PENDING)
    # An escalated change compresses the gap before the next phase to under a week: needs a remark and
    # hub-level approval (not the spoke alone).
    remarks: Mapped[str] = mapped_column(String(400), default="")
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_by_role: Mapped[str] = mapped_column(String(32), default="")
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    decided_by_role: Mapped[str] = mapped_column(String(32), default="")
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    """A message to the field team (site engineer / spokesperson) about a site.

    Written by the JIT scheduler: 3 days before a phase's end it warns that next-phase stock is about
    to dispatch, and again when the stock is dispatched, so work is never halted for want of material.
    """
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    spoke_id: Mapped[str] = mapped_column(String(48), default="", index=True)
    audience: Mapped[str] = mapped_column(String(24), default="field")  # field|site_engineer|spokesperson
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


class ProjectBOQ(Base):
    """A Bill of Quantities version for a project.

    `source` is the SE's BOQ, the external app's BOQ, or the reconciled `final` BOQ. Only a `final` BOQ
    goes through the spoke + hub approval gate; on full approval its lines become the site's operational
    BOM (reserved against hub stock).
    """
    __tablename__ = "project_boqs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    source: Mapped[str] = mapped_column(String(12), default=BOQ_CE)       # ce | external | final
    status: Mapped[str] = mapped_column(String(12), default=BOQ_DRAFT)    # draft|submitted|approved|rejected|superseded
    diff_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)  # vs the external BOQ
    spoke_approved_by: Mapped[str] = mapped_column(String(120), default="")
    hub_approved_by: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lines: Mapped[list["ProjectBOQLine"]] = relationship(back_populates="boq", cascade="all, delete-orphan")

    @property
    def code(self) -> str:
        return f"BOQ-{self.id}"


class ProjectBOQLine(Base):
    __tablename__ = "project_boq_lines"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    boq_id: Mapped[int] = mapped_column(ForeignKey("project_boqs.id"), index=True)
    material_id: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), default="")
    product_name: Mapped[str] = mapped_column(String(200), default="")
    phase_seq: Mapped[int] = mapped_column(Integer, default=0)
    total_qty: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    boq: Mapped["ProjectBOQ"] = relationship(back_populates="lines")


class BOQChangeRequest(Base):
    """A hub request to change an approved BOQ. Needs the spoke AND the SE to acknowledge."""
    __tablename__ = "boq_change_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    boq_id: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|resolved|rejected
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    spoke_acked: Mapped[bool] = mapped_column(Boolean, default=False)
    ce_acked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


ENQ_NEW = "new"
ENQ_CONTACTED = "contacted"
ENQ_CONVERTED = "converted"
ENQ_CLOSED = "closed"
ENQ_STATUSES = (ENQ_NEW, ENQ_CONTACTED, ENQ_CONVERTED, ENQ_CLOSED)


class Enquiry(Base):
    """A prospective customer's enquiry from the public portal. Routed by geofence to the covering
    spoke; if no spoke serves the location it routes to the hub (supervisor queue)."""
    __tablename__ = "enquiries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(String(600), default="")
    spoke_id: Mapped[str] = mapped_column(String(48), default="", index=True)  # covering spoke, or ""
    routed_to: Mapped[str] = mapped_column(String(8), default="hub")           # spoke | hub
    status: Mapped[str] = mapped_column(String(12), default=ENQ_NEW)
    handled_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancePartner(Base):
    """A preferred finance partner the internal finance team can route a project's funding to."""
    __tablename__ = "finance_partners"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="bank")  # bank | nbfc | internal
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectFinance(Base):
    """The finance record for a project (one per site): the internal finance team's progress securing
    funding for a captive project from a preferred partner."""
    __tablename__ = "project_finance"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=FIN_PENDING)
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    remarks: Mapped[str] = mapped_column(String(400), default="")
    handled_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectDocument(Base):
    """A file attached to a project: architect design (CAD/pdf) or a BOQ document.

    Binary lives in the DB (size-capped); moving to an object store is a later extension point.
    """
    __tablename__ = "project_documents"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="design")  # design|ce_boq|external_boq|final_boq|other
    filename: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(120), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by_role: Mapped[str] = mapped_column(String(32), default="")
    uploaded_by: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
