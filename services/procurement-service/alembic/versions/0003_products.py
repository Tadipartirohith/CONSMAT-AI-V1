"""vendor pricing at product level (brands)

Revision ID: 0003_products
Revises: 0002_procurement_orders
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_products"
down_revision = "0002_procurement_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate vendor_prices at product level (old material-level demo rows are reseeded).
    op.drop_table("vendor_prices")
    op.create_table(
        "vendor_prices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.String(length=48), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(14, 4), nullable=False),
        sa.Column("min_qty", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_id", "product_id", name="uq_vendor_product"),
    )
    op.create_index("ix_vprice_vendor", "vendor_prices", ["vendor_id"])
    op.create_index("ix_vprice_product", "vendor_prices", ["product_id"])
    op.create_index("ix_vprice_material", "vendor_prices", ["material_id"])

    op.add_column("procurement_lines", sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("procurement_lines", sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("procurement_lines", "product_name")
    op.drop_column("procurement_lines", "product_id")
    op.drop_index("ix_vprice_material", table_name="vendor_prices")
    op.drop_index("ix_vprice_product", table_name="vendor_prices")
    op.drop_index("ix_vprice_vendor", table_name="vendor_prices")
    op.drop_table("vendor_prices")
    op.create_table(
        "vendor_prices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.String(length=48), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("price", sa.Numeric(14, 4), nullable=False),
        sa.Column("min_qty", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_id", "material_id", name="uq_vendor_material"),
    )
