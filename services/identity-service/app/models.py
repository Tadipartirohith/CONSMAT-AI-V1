"""User accounts + roles for Consmat AI V1."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# All roles in the platform. `service` is reserved for internal service-to-service calls.
ROLES = (
    "admin",
    "hub_manager",
    "hub_supervisor",
    "spokesperson",
    "architect",
    "site_engineer",
    "finance",
    "consumer",
    "vendor",
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # email (lowercased)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    # links the user to their domain entity: spoke_id / consumer_id / vendor_id (else "")
    org_ref: Mapped[str] = mapped_column(String(64), default="")
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
