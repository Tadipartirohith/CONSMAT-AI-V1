"""Pydantic request/response models for the site API."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SpokeIn(BaseModel):
    name: str = Field(min_length=1)
    geofence: str = ""


class SpokeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    geofence: str
    active: bool


class AreaIn(BaseModel):
    area: str = Field(min_length=1)
    action: str = Field(default="add", pattern="^(add|remove)$")


class AreaRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spoke_id: str
    area: str
    action: str
    status: str
    requested_by: str
    requested_by_role: str
    decided_by: str
    created_at: datetime | None = None


class SpokeDetailOut(SpokeOut):
    areas: list[str] = []

    @classmethod
    def from_spoke(cls, spoke) -> "SpokeDetailOut":
        return cls(id=spoke.id, name=spoke.name, geofence=spoke.geofence, active=spoke.active,
                   areas=[a.area for a in spoke.areas])


class IntakeIn(BaseModel):
    name: str = Field(min_length=1)
    tier: str = "individual"
    location: str = Field(min_length=1)
    phone: str = ""
    email: str = ""
    fund_type: str = Field(default="", pattern="^(captive|client|)$")


class ConsumerUpdate(BaseModel):
    tier: str | None = None
    phone: str | None = None


class ConsumerIn(BaseModel):
    name: str = Field(min_length=1)
    tier: str = "individual"
    spoke_id: str
    phone: str = ""
    fund_type: str = Field(default="", pattern="^(captive|client|)$")


class ConsumerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    tier: str
    phone: str
    email: str = ""
    fund_type: str = ""
    spoke_id: str


class SiteIn(BaseModel):
    consumer_id: str
    label: str = ""
    location: str = ""
    area_sqft: float = Field(gt=0)
    floors: int = Field(default=1, ge=1)
    construction_type: str = "standard"
    project_type: str = Field(default="", pattern="^(captive|client|)$")


class SiteUpdate(BaseModel):
    project_type: str | None = Field(default=None, pattern="^(captive|client)$")
    stage: str | None = None


class BOMLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    product_id: str = ""
    product_name: str = ""
    phase_seq: int = 0
    total_qty: float


class BOMLineIn(BaseModel):
    material_id: str = Field(min_length=1)
    product_id: str = ""
    product_name: str = ""
    phase_seq: int = 0            # 0 = whole-project (auto-slice); 1-9 = explicit phase
    total_qty: float = Field(gt=0)


class SetBomIn(BaseModel):
    lines: list[BOMLineIn] = Field(min_length=1)


class PhaseProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phase_seq: int
    status: str
    planned_start: date | None = None
    planned_end: date | None = None
    completed_at: datetime | None = None


class PhaseDatesIn(BaseModel):
    start: date | None = None
    end: date | None = None
    remarks: str = ""


class PhaseDateChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    phase_seq: int
    old_end: date | None = None
    new_end: date
    status: str
    remarks: str = ""
    escalated: bool = False
    requested_by_role: str
    requested_by: str
    decided_by: str
    decided_at: datetime | None = None
    created_at: datetime | None = None


class DecideChangeIn(BaseModel):
    approve: bool


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    spoke_id: str
    audience: str
    phase_seq: int
    kind: str
    message: str
    read: bool
    created_at: datetime | None = None


class DispatchLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    product_id: str = ""
    product_name: str = ""
    qty: float
    status: str


class DispatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    phase_seq: int
    status: str
    received_at: datetime | None = None
    created_at: datetime | None = None
    lines: list[DispatchLineOut] = []


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    consumer_id: str
    label: str
    location: str
    area_sqft: float
    floors: int
    construction_type: str
    status: str
    project_type: str = ""
    stage: str = ""
    budget: float | None = None
    payment_received: bool = False
    total_area: float
    bom_lines: list[BOMLineOut] = []
    phases: list[PhaseProgressOut] = []
    dispatches: list[DispatchOut] = []


class ProjectBOQLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    product_id: str = ""
    product_name: str = ""
    phase_seq: int = 0
    total_qty: float


class ProjectBOQOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    site_id: int
    source: str
    status: str
    diff_pct: float | None = None
    spoke_approved_by: str = ""
    hub_approved_by: str = ""
    note: str = ""
    created_by: str = ""
    created_at: datetime | None = None
    lines: list[ProjectBOQLineOut] = []


class BOQChangeIn(BaseModel):
    note: str = Field(min_length=1)


class BOQChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    boq_id: int
    note: str
    status: str
    requested_by: str
    spoke_acked: bool
    ce_acked: bool
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class EnquiryIn(BaseModel):
    name: str = Field(min_length=1)
    phone: str = ""
    email: str = ""
    location: str = Field(min_length=1)
    message: str = ""


class EnquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    email: str
    location: str
    message: str
    spoke_id: str
    routed_to: str
    status: str
    handled_by: str
    created_at: datetime | None = None


class EnquiryUpdate(BaseModel):
    status: str | None = None


class EnquiryResult(BaseModel):
    id: int
    routed_to: str
    spoke: str | None = None


class FinancePartnerIn(BaseModel):
    name: str = Field(min_length=1)
    kind: str = Field(default="bank", pattern="^(bank|nbfc|internal)$")
    note: str = ""


class FinancePartnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    kind: str
    active: bool
    note: str


class ProjectFinanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    status: str
    partner_id: int | None = None
    amount: float | None = None
    remarks: str
    handled_by: str
    created_at: datetime | None = None
    decided_at: datetime | None = None


class ProjectFinanceUpdate(BaseModel):
    status: str | None = None
    partner_id: int | None = None
    amount: float | None = None
    remarks: str | None = None


class ProjectDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    kind: str
    filename: str
    content_type: str
    size: int
    uploaded_by_role: str
    uploaded_by: str
    note: str
    created_at: datetime | None = None


class PhaseRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    seq: int
    name: str
    repeats_per_floor: bool
