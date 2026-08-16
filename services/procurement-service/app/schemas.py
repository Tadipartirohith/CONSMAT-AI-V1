"""Pydantic request/response models for the procurement API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    material_id: str
    brand: str
    product_name: str
    price: float
    min_qty: float
    updated_at: datetime | None = None


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    city: str
    phone: str
    gstin: str
    is_hub_self: bool
    active: bool
    created_at: datetime | None = None


class VendorDetailOut(VendorOut):
    prices: list[PriceOut] = []


class VendorIn(BaseModel):
    name: str = Field(min_length=1)
    city: str = ""
    phone: str = ""
    gstin: str = ""
    is_hub_self: bool = False


class VendorUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    phone: str | None = None
    gstin: str | None = None
    active: bool | None = None


class PriceIn(BaseModel):
    product_id: str = Field(min_length=1)
    price: float = Field(ge=0)
    min_qty: float = Field(default=0, ge=0)


class MarketPriceOut(BaseModel):
    vendor_id: str
    vendor_name: str
    is_hub_self: bool
    material_id: str
    product_id: str
    brand: str
    product_name: str
    price: float
    min_qty: float
    city: str


# ---- Procurement engine / LLM / orders ----

class DemandLine(BaseModel):
    material_id: str = Field(min_length=1)
    qty: float = Field(gt=0)


class PlanIn(BaseModel):
    demand: list[DemandLine] = Field(min_length=1)


class AnalyzeIn(BaseModel):
    demand: list[DemandLine] = Field(min_length=1)
    selling_prices: dict[str, float] | None = None
    # if selling_prices is omitted but a tier is given, fetch prices from pricing-service
    tier: str | None = None


class OrderLineIn(BaseModel):
    material_id: str = Field(min_length=1)
    product_id: str = ""
    product_name: str = ""
    vendor_id: str = Field(min_length=1)
    qty: float = Field(gt=0)
    unit_cost: float = Field(ge=0)


class OrderIn(BaseModel):
    lines: list[OrderLineIn] = Field(min_length=1)
    note: str = ""


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
    product_name: str
    vendor_id: str
    vendor_name: str
    qty: float
    unit_cost: float
    received: bool


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    status: str
    total_cost: float
    note: str
    created_at: datetime | None = None
    received_at: datetime | None = None
    lines: list[OrderLineOut] = []
