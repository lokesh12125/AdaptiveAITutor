"""Remember what each reflection question asked about, and the tutor's reply to the answer.

Revision ID: 0005
Revises: 0004
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reflections", sa.Column("kind", sa.String(40), nullable=True))
    op.add_column("reflections", sa.Column("context", JSONB(), server_default="{}", nullable=False))
    op.add_column("reflections", sa.Column("feedback", sa.Text(), nullable=True))
    op.add_column("reflections", sa.Column("quality", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("reflections", "quality")
    op.drop_column("reflections", "feedback")
    op.drop_column("reflections", "context")
    op.drop_column("reflections", "kind")
