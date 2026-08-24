"""finance partners + per-project finance record

Revision ID: 0012_finance
Revises: 0011_project_boq
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_finance"
down_revision = "0011_project_boq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_partners",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="bank"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "project_finance",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("partner_id", sa.Integer, nullable=True),
        sa.Column("amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("remarks", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("handled_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projfin_site", "project_finance", ["site_id"])
    # seed a few preferred finance partners for the demo
    op.execute("INSERT INTO finance_partners (name, kind, note) VALUES "
               "('HDFC Bank', 'bank', 'Preferred banking partner'),"
               "('Bajaj Finserv', 'nbfc', 'Preferred NBFC partner'),"
               "('Consmat Capital', 'internal', 'In-house captive funding')")


def downgrade() -> None:
    op.drop_index("ix_projfin_site", table_name="project_finance")
    op.drop_table("project_finance")
    op.drop_table("finance_partners")
