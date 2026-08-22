"""escrow: released_amount + released_at (funds held until delivery confirmed)

Revision ID: 0002_escrow
Revises: 0001_initial
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_escrow"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("released_amount", sa.Numeric(16, 2), nullable=False,
                                        server_default="0"))
    op.add_column("payments", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "released_at")
    op.drop_column("payments", "released_amount")
