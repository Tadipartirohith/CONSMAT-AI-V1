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


class VendorRequestIn(BaseModel):
    action: str = Field(pattern="^(add|remove)$")
    vendor_id: str = ""          # required for remove
    name: str = ""               # required for add
    city: str = ""
    phone: str = ""
    gstin: str = ""
    is_hub_self: bool = False
    reason: str = ""


class VendorRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action: str
    vendor_id: str
    name: str
    city: str
    phone: str
    gstin: str
    is_hub_self: bool
    reason: str
    status: str
    requested_by_role: str
    requested_by: str
    decided_by: str
    created_at: datetime | None = None
    decided_at: datetime | None = None


class DecideVendorIn(BaseModel):
    approve: bool


class AlertIn(BaseModel):
    material_id: str = ""
    query: str = ""
    op: str = Field(default="lt", pattern="^(lt|lte|gt|gte|eq)$")
    value: float = Field(ge=0)
    seller: str = ""
    location: str = ""


class ScanIn(BaseModel):
    category: str = ""   # "" = all categories


class PriceIn(BaseModel):
    product_id: str = Field(min_length=1)
    price: float = Field(ge=0)
    min_qty: float = Field(default=0, ge=0)


class ExternalOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: str
    product_name: str
    source: str
    seller: str
    price: float
    url: str
    confidence: str
    note: str


class ScoutIn(BaseModel):
    material_id: str = Field(min_length=1)
    material_name: str = ""


class ImportOffer(BaseModel):
    material_id: str = Field(min_length=1)
    product_name: str = ""
    seller: str = ""
    price: float = Field(ge=0)
    url: str = ""


class ImportIn(BaseModel):
    offers: list[ImportOffer] = Field(min_length=1)


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
    product_id: str = ""      # optional: procure this specific product (brand); else cheapest brand
    product_name: str = ""    # optional: for clearer messaging when unavailable
    qty: float = Field(gt=0)


class PlanIn(BaseModel):
    demand: list[DemandLine] = Field(min_length=1)


class AnalyzeIn(BaseModel):
    demand: list[DemandLine] = Field(min_length=1)
    # Procurement is tier-agnostic (buying doesn't depend on who we sell to). Profitability is a
    # reference lens: computed against the hub's LIST price unless explicit selling_prices are given.
    selling_prices: dict[str, float] | None = None


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
