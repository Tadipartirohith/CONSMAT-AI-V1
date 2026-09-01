"""quality control (lab tests + GRN inspection), handover/completion, consumer segment

Revision ID: 0017_quality_completion
Revises: 0016_finance_eligibility
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_quality_completion"
down_revision = "0016_finance_eligibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # goods-receipt inspection on dispatch (GRN)
    op.add_column("dispatches", sa.Column("qc_result", sa.String(length=10), nullable=False,
                                          server_default="pending"))
    op.add_column("dispatches", sa.Column("qc_note", sa.String(length=400), nullable=False,
                                          server_default=""))
    # handover / completion certificate on site
    op.add_column("sites", sa.Column("handed_over", sa.Boolean(), nullable=False,
                                     server_default=sa.false()))
    op.add_column("sites", sa.Column("completion_ref", sa.String(length=40), nullable=False,
                                     server_default=""))
    # B2B/B2C segment on consumer
    op.add_column("consumers", sa.Column("segment", sa.String(length=20), nullable=False,
                                         server_default=""))
    # quality lab tests
    op.create_table(
        "lab_tests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), index=True, nullable=False),
        sa.Column("material", sa.String(length=40), nullable=False, server_default="cement"),
        sa.Column("test_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("result", sa.String(length=10), nullable=False, server_default="pending"),
        sa.Column("report_ref", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("remarks", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("tested_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # snag list
    op.create_table(
        "snags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), index=True, nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="open"),
        sa.Column("raised_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fixed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("snags")
    op.drop_table("lab_tests")
    op.drop_column("consumers", "segment")
    op.drop_column("sites", "completion_ref")
    op.drop_column("sites", "handed_over")
    op.drop_column("dispatches", "qc_note")
    op.drop_column("dispatches", "qc_result")
