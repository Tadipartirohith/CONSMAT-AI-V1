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


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    material_id: str
    brand: str
    name: str
    grade: str
    unit: str
    active: bool


class ProductIn(BaseModel):
    material_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    brand: str = ""
    grade: str = ""
    unit: str = ""


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    on_hand: float
    reserved: float
    available: float
    avg_cost: float
    updated_at: datetime | None = None


class ProductStockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    material_id: str
    on_hand: float
    reserved: float
    available: float
    avg_cost: float
    updated_at: datetime | None = None


class LowStockOut(BaseModel):
    product_id: str
    material_id: str
    on_hand: float
    reserved: float
    buffer_target: float
    shortfall: float
    status: str


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: str
    product_id: str = ""
    direction: str
    qty: float
    unit_cost: float
    balance_after: float
    ref_type: str
    ref_id: str
    note: str
    at: datetime


class InboundIn(BaseModel):
    material_id: str = ""            # optional when product_id is given (derived from the product)
    product_id: str = ""            # when set, stock moves at the brand level (rolls up to material)
    qty: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    ref_type: str = "procurement"
    ref_id: str = ""
    note: str = ""


class OutboundIn(BaseModel):
    material_id: str = ""
    product_id: str = ""
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
    material_id: str = ""
    product_id: str = ""
    qty: float = Field(gt=0)
    allow_over: bool = False    # reserve committed demand even beyond on-hand (3x-buffer signal)
