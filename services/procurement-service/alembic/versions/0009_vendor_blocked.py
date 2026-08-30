"""vendor blacklist flag

Revision ID: 0009_vendor_blocked
Revises: 0008_market_snapshots
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_vendor_blocked"
down_revision = "0008_market_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendors", sa.Column("blocked", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("vendors", "blocked")
