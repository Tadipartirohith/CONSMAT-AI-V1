"""project documents (design/BOQ files attached to a project)

Revision ID: 0010_project_documents
Revises: 0009_project_lifecycle
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_project_documents"
down_revision = "0009_project_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="design"),
        sa.Column("filename", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("uploaded_by_role", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("uploaded_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_projectdoc_site", "project_documents", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_projectdoc_site", table_name="project_documents")
    op.drop_table("project_documents")
