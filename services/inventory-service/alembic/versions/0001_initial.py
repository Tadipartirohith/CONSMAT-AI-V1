"""initial inventory schema: materials, inventory_items, ledger_entries

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
        "materials",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("grade", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("per_sqft", sa.Numeric(12, 5), nullable=False, server_default="0"),
    )
    op.create_table(
        "inventory_items",
        sa.Column("material_id", sa.String(length=40), sa.ForeignKey("materials.id"), primary_key=True),
        sa.Column("on_hand", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("direction", sa.String(length=12), nullable=False),
        sa.Column("qty", sa.Numeric(16, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("balance_after", sa.Numeric(16, 3), nullable=False),
        sa.Column("ref_type", sa.String(length=24), nullable=False, server_default="adjustment"),
        sa.Column("ref_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ledger_material", "ledger_entries", ["material_id"])
    op.create_index("ix_ledger_at", "ledger_entries", ["at"])


def downgrade() -> None:
    op.drop_index("ix_ledger_at", table_name="ledger_entries")
    op.drop_index("ix_ledger_material", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_table("inventory_items")
    op.drop_table("materials")
