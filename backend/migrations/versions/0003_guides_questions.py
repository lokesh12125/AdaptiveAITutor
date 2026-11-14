"""Topic guides, problem patterns, and what the learner asked when a hint answers a question.

Non-destructive: three nullable columns.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("units", sa.Column("guide", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("problems", sa.Column("pattern", sa.String(length=64), nullable=True))
    op.add_column("hints", sa.Column("learner_request", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("hints", "learner_request")
    op.drop_column("problems", "pattern")
    op.drop_column("units", "guide")
