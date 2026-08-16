"""initial procurement schema: vendors, vendor_prices

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
        "vendors",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("gstin", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("is_hub_self", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
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
    op.create_index("ix_vprice_vendor", "vendor_prices", ["vendor_id"])
    op.create_index("ix_vprice_material", "vendor_prices", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_vprice_material", table_name="vendor_prices")
    op.drop_index("ix_vprice_vendor", table_name="vendor_prices")
    op.drop_table("vendor_prices")
    op.drop_table("vendors")
