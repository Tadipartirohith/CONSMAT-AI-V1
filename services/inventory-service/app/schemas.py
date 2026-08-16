"""Pydantic request/response models for the inventory API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    category: str
    unit: str
    grade: str
    per_sqft: float


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    on_hand: float
    reserved: float
    available: float
    avg_cost: float
    updated_at: datetime | None = None


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: str
    direction: str
    qty: float
    unit_cost: float
    balance_after: float
    ref_type: str
    ref_id: str
    note: str
    at: datetime


class InboundIn(BaseModel):
    material_id: str
    qty: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    ref_type: str = "procurement"
    ref_id: str = ""
    note: str = ""


class OutboundIn(BaseModel):
    material_id: str
    qty: float = Field(gt=0)
    ref_type: str = "dispatch"
    ref_id: str = ""
    note: str = ""
    from_reservation: bool = False


class AdjustIn(BaseModel):
    material_id: str
    qty_delta: float
    note: str = ""


class ReserveIn(BaseModel):
    material_id: str
    qty: float = Field(gt=0)
