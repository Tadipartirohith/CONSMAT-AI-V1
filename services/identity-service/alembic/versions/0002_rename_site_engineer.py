"""rename role civil_engineer -> site_engineer (and civil@ -> site@)

Revision ID: 0002_rename_site_engineer
Revises: 0001_initial
Create Date: 2026-08-24
"""
from alembic import op

revision = "0002_rename_site_engineer"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename the demo login first (so the reseed does not create a duplicate), then the role globally.
    op.execute("UPDATE users SET id='site@consmat.com', name='Site Engineer' "
               "WHERE id='civil@consmat.com'")
    op.execute("UPDATE users SET role='site_engineer' WHERE role='civil_engineer'")


def downgrade() -> None:
    op.execute("UPDATE users SET role='civil_engineer' WHERE role='site_engineer'")
    op.execute("UPDATE users SET id='civil@consmat.com', name='Civil Engineer' "
               "WHERE id='site@consmat.com'")
