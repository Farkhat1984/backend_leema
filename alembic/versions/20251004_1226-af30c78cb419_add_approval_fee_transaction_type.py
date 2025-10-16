"""Add APPROVAL_FEE transaction type

Revision ID: af30c78cb419
Revises: 839dce997838
Create Date: 2025-10-04 12:26:25.926012

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af30c78cb419'
down_revision = '839dce997838'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add APPROVAL_FEE to TransactionType enum in PostgreSQL
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'APPROVAL_FEE'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values easily
    # You would need to recreate the type and update all dependent objects
    # For simplicity, we'll leave it as is
    pass
