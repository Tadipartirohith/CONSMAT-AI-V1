"""Pydantic request/response models for the payment API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentIn(BaseModel):
    ref: str = ""
    consumer_id: str = ""
    amount: float = Field(gt=0)
    currency: str = ""
    note: str = ""


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    ref: str
    consumer_id: str
    amount: float
    currency: str
    provider: str
    provider_ref: str
    status: str
    note: str
    created_at: datetime | None = None
    paid_at: datetime | None = None


class ConfigOut(BaseModel):
    provider: str
    currency: str
    enabled: bool
