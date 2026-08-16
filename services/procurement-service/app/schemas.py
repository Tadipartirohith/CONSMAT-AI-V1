"""Pydantic request/response models for the procurement API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_id: str
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
    material_id: str = Field(min_length=1)
    price: float = Field(ge=0)
    min_qty: float = Field(default=0, ge=0)


class MarketPriceOut(BaseModel):
    vendor_id: str
    vendor_name: str
    is_hub_self: bool
    material_id: str
    price: float
    min_qty: float
    city: str
