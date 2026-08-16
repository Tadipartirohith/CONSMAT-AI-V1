"""Pydantic request/response models for the site API."""
from __future__ import annotations

from datetime import datetime

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


class ConsumerUpdate(BaseModel):
    tier: str | None = None
    phone: str | None = None


class ConsumerIn(BaseModel):
    name: str = Field(min_length=1)
    tier: str = "individual"
    spoke_id: str
    phone: str = ""


class ConsumerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    tier: str
    phone: str
    spoke_id: str


class SiteIn(BaseModel):
    consumer_id: str
    label: str = ""
    location: str = ""
    area_sqft: float = Field(gt=0)
    floors: int = Field(default=1, ge=1)
    construction_type: str = "standard"


class BOMLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    total_qty: float


class PhaseProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phase_seq: int
    status: str
    completed_at: datetime | None = None


class DispatchLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    qty: float
    status: str


class DispatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    phase_seq: int
    status: str
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
    total_area: float
    bom_lines: list[BOMLineOut] = []
    phases: list[PhaseProgressOut] = []
    dispatches: list[DispatchOut] = []


class PhaseRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    seq: int
    name: str
    repeats_per_floor: bool
