"""Pydantic request/response models for the identity API."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    role: str
    org_ref: str
    active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=4)
    name: str = ""
    role: str
    org_ref: str = ""


class UserUpdate(BaseModel):
    role: str | None = None
    active: bool | None = None
    org_ref: str | None = None
    name: str | None = None
