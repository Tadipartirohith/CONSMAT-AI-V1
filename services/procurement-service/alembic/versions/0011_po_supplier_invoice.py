"""supplier invoice on PO for 3-way match (ordered <-> GRN <-> invoiced) - PDF stage 13

Revision ID: 0011_po_supplier_invoice
Revises: 0010_rfq
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_po_supplier_invoice"
down_revision = "0010_rfq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("procurement_orders", sa.Column("supplier_invoice", sa.Numeric(16, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("procurement_orders", "supplier_invoice")
