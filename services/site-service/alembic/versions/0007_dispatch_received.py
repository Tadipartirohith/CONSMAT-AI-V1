"""dispatch received_at (customer confirm-receipt)

Revision ID: 0007_dispatch_received
Revises: 0006_bom_phase_seq
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_dispatch_received"
down_revision = "0006_bom_phase_seq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dispatches", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("dispatches", "received_at")
