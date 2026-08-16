"""product-level stock + ledger product_id

Revision ID: 0003_product_stock
Revises: 0002_products
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_product_stock"
down_revision = "0002_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_stock",
        sa.Column("product_id", sa.String(length=64), sa.ForeignKey("products.id"), primary_key=True),
        sa.Column("material_id", sa.String(length=40), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("on_hand", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pstock_material", "product_stock", ["material_id"])
    # brand SKU attached to each ledger movement when known
    op.add_column("ledger_entries",
                  sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""))
    op.create_index("ix_ledger_product", "ledger_entries", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_ledger_product", table_name="ledger_entries")
    op.drop_column("ledger_entries", "product_id")
    op.drop_index("ix_pstock_material", table_name="product_stock")
    op.drop_table("product_stock")
