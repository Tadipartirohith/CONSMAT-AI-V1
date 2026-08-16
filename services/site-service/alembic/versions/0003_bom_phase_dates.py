"""product-level BOM, phase dates, and phase date-change approvals

Revision ID: 0003_bom_phase_dates
Revises: 0002_spoke_areas
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_bom_phase_dates"
down_revision = "0002_spoke_areas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bom_lines", sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("bom_lines", sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""))

    op.add_column("phase_progress", sa.Column("planned_start", sa.Date(), nullable=True))
    op.add_column("phase_progress", sa.Column("planned_end", sa.Date(), nullable=True))
    op.add_column("phase_progress", sa.Column("dispatched", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("dispatch_lines", sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("dispatch_lines", sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""))

    op.create_table(
        "phase_date_changes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("phase_seq", sa.Integer, nullable=False),
        sa.Column("old_end", sa.Date(), nullable=True),
        sa.Column("new_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("requested_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("requested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("decided_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("decided_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pdc_site", "phase_date_changes", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_pdc_site", table_name="phase_date_changes")
    op.drop_table("phase_date_changes")
    op.drop_column("dispatch_lines", "product_name")
    op.drop_column("dispatch_lines", "product_id")
    op.drop_column("phase_progress", "dispatched")
    op.drop_column("phase_progress", "planned_end")
    op.drop_column("phase_progress", "planned_start")
    op.drop_column("bom_lines", "product_name")
    op.drop_column("bom_lines", "product_id")
