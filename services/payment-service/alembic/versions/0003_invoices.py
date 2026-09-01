"""client progress invoices (billing) - PDF stage 13

Revision ID: 0003_invoices
Revises: 0002_escrow
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_invoices"
down_revision = "0002_escrow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ref", sa.String(length=64), index=True, nullable=False, server_default=""),
        sa.Column("consumer_id", sa.String(length=64), index=True, nullable=False, server_default=""),
        sa.Column("phase_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="issued"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("invoices")
