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
    escrow: bool = True   # hold funds and release on delivery confirmation


class ReleaseIn(BaseModel):
    ref: str = Field(min_length=1)
    fraction: float = Field(ge=0, le=1)   # portion of each held payment to release (deliveries confirmed)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    ref: str
    consumer_id: str
    amount: float
    released_amount: float = 0
    currency: str
    provider: str
    provider_ref: str
    status: str
    note: str
    created_at: datetime | None = None
    paid_at: datetime | None = None
    released_at: datetime | None = None


class ConfigOut(BaseModel):
    provider: str
    currency: str
    enabled: bool


class InvoiceIn(BaseModel):
    ref: str = ""
    consumer_id: str = ""
    amount: float = Field(gt=0)
    phase_seq: int = 0
    title: str = ""
    note: str = ""
    currency: str = ""


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    ref: str
    consumer_id: str
    phase_seq: int
    title: str
    amount: float
    currency: str
    status: str
    note: str
    payment_id: int | None = None
    created_at: datetime | None = None
    paid_at: datetime | None = None
