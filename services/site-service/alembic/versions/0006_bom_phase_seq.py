"""explicit per-phase BOM (bom_lines.phase_seq)

Revision ID: 0006_bom_phase_seq
Revises: 0005_email_area_requests
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_bom_phase_seq"
down_revision = "0005_email_area_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bom_lines", sa.Column("phase_seq", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("bom_lines", "phase_seq")
