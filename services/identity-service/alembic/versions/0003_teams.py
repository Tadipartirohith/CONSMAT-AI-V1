"""teams + team membership (OpenStack-style projects)

Revision ID: 0003_teams
Revises: 0002_rename_site_engineer
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_teams"
down_revision = "0002_rename_site_engineer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("spoke_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=False, index=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="member"),
        sa.Column("granted_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )


def downgrade() -> None:
    op.drop_table("team_members")
    op.drop_table("teams")
