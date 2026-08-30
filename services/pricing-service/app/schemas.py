"""Pydantic request/response models for the pricing API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RuleIn(BaseModel):
    product_id: str | None = None
    material_id: str | None = None
    tier: str | None = None
    margin_pct: float = Field(ge=0)


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: str | None = None
    material_id: str | None
    tier: str | None
    margin_pct: float
    updated_at: datetime | None = None


class PriceOut(BaseModel):
    material_id: str
    tier: str | None
    landed_cost: float
    margin_pct: float
    rule: str
    unit_price: float


class ProductPriceOut(BaseModel):
    product_id: str
    material_id: str
    tier: str | None
    landed_cost: float
    margin_pct: float
    rule: str
    unit_price: float


class QuoteItem(BaseModel):
    material_id: str = Field(min_length=1)
    qty: float = Field(gt=0)


class QuoteIn(BaseModel):
    tier: str | None = None
    items: list[QuoteItem] = Field(min_length=1)


class ProductQuoteItem(BaseModel):
    product_id: str = Field(min_length=1)
    qty: float = Field(gt=0)


class ProductQuoteIn(BaseModel):
    tier: str | None = None
    items: list[ProductQuoteItem] = Field(min_length=1)


class ProductPricesIn(BaseModel):
    product_ids: list[str] = Field(min_length=1)
    tier: str | None = None
