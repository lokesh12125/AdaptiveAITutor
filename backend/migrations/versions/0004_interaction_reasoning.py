"""Keep the reasoning behind each hint, and what the learner did next.

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("interaction_records", sa.Column("reasoning", JSONB(), server_default="{}", nullable=False))
    op.add_column("interaction_records", sa.Column("next_action", JSONB(), nullable=True))
    op.add_column("interaction_records", sa.Column("resolved", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("interaction_records", "resolved")
    op.drop_column("interaction_records", "next_action")
    op.drop_column("interaction_records", "reasoning")
