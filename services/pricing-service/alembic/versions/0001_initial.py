"""initial pricing schema: margin_rules

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "margin_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), nullable=True),
        sa.Column("tier", sa.String(length=20), nullable=True),
        sa.Column("margin_pct", sa.Numeric(6, 3), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_margin_lookup", "margin_rules", ["material_id", "tier"])


def downgrade() -> None:
    op.drop_index("ix_margin_lookup", table_name="margin_rules")
    op.drop_table("margin_rules")
