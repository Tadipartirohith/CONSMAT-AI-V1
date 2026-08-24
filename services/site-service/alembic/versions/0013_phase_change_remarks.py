"""phase-date change: remarks + escalated (the <1-week rule)

Revision ID: 0013_phase_change_remarks
Revises: 0012_finance
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_phase_change_remarks"
down_revision = "0012_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("phase_date_changes", sa.Column("remarks", sa.String(length=400), nullable=False, server_default=""))
    op.add_column("phase_date_changes", sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("phase_date_changes", "escalated")
    op.drop_column("phase_date_changes", "remarks")
