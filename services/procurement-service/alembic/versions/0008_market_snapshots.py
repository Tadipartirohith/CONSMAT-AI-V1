"""daily market price snapshots (per-segment movement + outlook)

Revision ID: 0008_market_snapshots
Revises: 0007_order_requests
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_market_snapshots"
down_revision = "0007_order_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("snap_date", sa.Date, nullable=False),
        sa.Column("avg_price", sa.Numeric(14, 4), nullable=False),
        sa.UniqueConstraint("material_id", "snap_date", name="uq_snap_mat_date"),
    )
    op.create_index("ix_snap_material", "market_snapshots", ["material_id"])
    op.create_index("ix_snap_date", "market_snapshots", ["snap_date"])


def downgrade() -> None:
    op.drop_index("ix_snap_date", table_name="market_snapshots")
    op.drop_index("ix_snap_material", table_name="market_snapshots")
    op.drop_table("market_snapshots")
