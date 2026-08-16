"""product catalog (branded SKUs under materials)

Revision ID: 0002_products
Revises: 0001_initial
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_products"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("material_id", sa.String(length=40), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("grade", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_product_material", "products", ["material_id"])
    # case-insensitive substring search over the full product name
    op.execute("CREATE INDEX ix_product_name_lower ON products (lower(name))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_product_name_lower")
    op.drop_index("ix_product_material", table_name="products")
    op.drop_table("products")
