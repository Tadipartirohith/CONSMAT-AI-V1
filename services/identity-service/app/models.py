"""User accounts + roles + teams for Consmat AI V1."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# All roles in the platform. `service` is reserved for internal service-to-service calls.
ROLES = (
    "admin",
    "hub_manager",
    "hub_supervisor",
    "hr",
    "spokesperson",
    "architect",
    "site_engineer",
    "finance",
    "consumer",
    "vendor",
)

# Role a member holds inside a team (OpenStack-style: a project has admin / member / reader).
TEAM_ROLES = ("admin", "member", "viewer")


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


class Team(Base):
    """A team (OpenStack-style project/tenant): a named container users are assigned into with a role.
    Membership + the member's team-role are the grant; they are handed out and revoked by a team admin,
    HR, or the org admin. `spoke_id` optionally scopes the team to one branch."""
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    spoke_id: Mapped[str] = mapped_column(String(64), default="")   # optional branch this team belongs to
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """A user's role assignment inside a team. Unique per (team, user)."""
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)   # user email
    role: Mapped[str] = mapped_column(String(24), default="member")                # admin | member | viewer
    granted_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped["Team"] = relationship(back_populates="members")
