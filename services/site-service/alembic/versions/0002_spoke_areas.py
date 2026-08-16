"""spoke coverage areas (geofence)

Revision ID: 0002_spoke_areas
Revises: 0001_initial
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_spoke_areas"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spoke_areas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("spoke_id", sa.String(length=48), sa.ForeignKey("spokes.id"), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("spoke_id", "area", name="uq_spoke_area"),
    )
    op.create_index("ix_area_spoke", "spoke_areas", ["spoke_id"])


def downgrade() -> None:
    op.drop_index("ix_area_spoke", table_name="spoke_areas")
    op.drop_table("spoke_areas")
