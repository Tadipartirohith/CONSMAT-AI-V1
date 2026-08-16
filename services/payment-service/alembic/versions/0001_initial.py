"""initial payment schema: payments

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
        "payments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("consumer_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
        sa.Column("provider", sa.String(length=24), nullable=False, server_default="mock"),
        sa.Column("provider_ref", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payment_ref", "payments", ["ref"])
    op.create_index("ix_payment_consumer", "payments", ["consumer_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_consumer", table_name="payments")
    op.drop_index("ix_payment_ref", table_name="payments")
    op.drop_table("payments")
