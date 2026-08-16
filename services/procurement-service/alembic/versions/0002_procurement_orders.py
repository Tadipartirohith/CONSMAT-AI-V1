"""procurement orders + lines

Revision ID: 0002_procurement_orders
Revises: 0001_initial
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_procurement_orders"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_orders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="approved"),
        sa.Column("total_cost", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "procurement_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("procurement_orders.id"), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("vendor_id", sa.String(length=48), nullable=False),
        sa.Column("vendor_name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(16, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("received", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_pline_order", "procurement_lines", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_pline_order", table_name="procurement_lines")
    op.drop_table("procurement_lines")
    op.drop_table("procurement_orders")
