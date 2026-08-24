"""project BOQ versions + BOQ change requests

Revision ID: 0011_project_boq
Revises: 0010_project_documents
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_project_boq"
down_revision = "0010_project_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_boqs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("source", sa.String(length=12), nullable=False, server_default="ce"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="draft"),
        sa.Column("diff_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("spoke_approved_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("hub_approved_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_boq_site", "project_boqs", ["site_id"])
    op.create_table(
        "project_boq_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("boq_id", sa.Integer, sa.ForeignKey("project_boqs.id"), nullable=False),
        sa.Column("material_id", sa.String(length=40), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("product_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("phase_seq", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_qty", sa.Numeric(16, 3), nullable=False),
    )
    op.create_index("ix_boqline_boq", "project_boq_lines", ["boq_id"])
    op.create_table(
        "boq_change_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("boq_id", sa.Integer, nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("spoke_acked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ce_acked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_boqcr_site", "boq_change_requests", ["site_id"])


def downgrade() -> None:
    op.drop_table("boq_change_requests")
    op.drop_index("ix_boqline_boq", table_name="project_boq_lines")
    op.drop_table("project_boq_lines")
    op.drop_index("ix_boq_site", table_name="project_boqs")
    op.drop_table("project_boqs")
