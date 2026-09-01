"""RFQ (request for quotation) + vendor channel kind (supplier/oem)

Revision ID: 0010_rfq
Revises: 0009_vendor_blocked
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_rfq"
down_revision = "0009_vendor_blocked"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendors", sa.Column("kind", sa.String(length=12), nullable=False,
                                       server_default="supplier"))
    op.create_table(
        "rfqs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("qty", sa.Numeric(16, 3), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="open"),
        sa.Column("created_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("awarded_vendor_id", sa.String(length=48), nullable=False, server_default=""),
        sa.Column("awarded_quote_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "rfq_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rfq_id", sa.Integer(), sa.ForeignKey("rfqs.id"), index=True, nullable=False),
        sa.Column("vendor_id", sa.String(length=48), nullable=False),
        sa.Column("vendor_name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_terms", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("quality_note", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rfq_quotes")
    op.drop_table("rfqs")
    op.drop_column("vendors", "kind")
