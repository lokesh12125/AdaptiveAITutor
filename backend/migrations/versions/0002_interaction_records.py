"""Persistent interaction state, plus notes on imported questions.

Non-destructive. Existing completed cycles are copied into interaction_records, so learners keep their
history. Those older rows have no retrieval result or full decision, because neither was stored then.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("problems", sa.Column("learner_notes", sa.Text(), nullable=True))
    op.create_table(
        "interaction_records",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("problem_id", sa.String(length=96), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_id", sa.String(length=32), nullable=False),
        sa.Column("evaluation_id", sa.String(length=32), nullable=True),
        sa.Column("evaluation_kind", sa.String(length=12), nullable=True),
        sa.Column("trigger", sa.String(length=24), nullable=False),
        sa.Column("verdict", sa.String(length=24), nullable=True),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("tests_passed", sa.Integer(), nullable=False),
        sa.Column("tests_total", sa.Integer(), nullable=False),
        sa.Column("code_changed", sa.Boolean(), nullable=False),
        sa.Column("learner_input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("diagnostic", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cognitive", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieval", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hint_id", sa.String(length=32), nullable=True),
        sa.Column("active_seconds", sa.Integer(), nullable=True),
        sa.Column("policy_version", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hint_id"], ["hints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["code_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_interaction_records_user_id", "interaction_records", ["user_id"])
    op.create_index("ix_interaction_user_problem_time", "interaction_records", ["user_id", "problem_id", "created_at"])
    op.execute(
        """
        INSERT INTO interaction_records (
            id, run_id, user_id, problem_id, unit_id, snapshot_id, evaluation_id, evaluation_kind, trigger, verdict, category, issue_key,
            tests_passed, tests_total, code_changed, learner_input, diagnostic, cognitive, retrieval, decision, hint_id, active_seconds, policy_version, created_at
        )
        SELECT
            replace(gen_random_uuid()::text, '-', ''), r.id, r.user_id, r.problem_id, p.unit_id, r.snapshot_id, r.evaluation_id, e.kind, r.trigger, e.verdict, d.category, d.issue_key,
            COALESCE(e.passed, 0), COALESCE(e.total, 0),
            r.snapshot_id IS DISTINCT FROM LAG(r.snapshot_id) OVER (PARTITION BY r.user_id, r.problem_id ORDER BY r.created_at),
            '{}'::jsonb, COALESCE(d.data, '{}'::jsonb), '{}'::jsonb, NULL, '{}'::jsonb,
            (SELECT h.id FROM hints h WHERE h.run_id = r.id LIMIT 1), e.active_seconds, r.policy_version, r.created_at
        FROM pipeline_runs r
        JOIN diagnostics d ON d.run_id = r.id
        JOIN problems p ON p.id = r.problem_id
        LEFT JOIN evaluations e ON e.id = r.evaluation_id
        WHERE r.status = 'completed'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_interaction_user_problem_time", table_name="interaction_records")
    op.drop_index("ix_interaction_records_user_id", table_name="interaction_records")
    op.drop_table("interaction_records")
    op.drop_column("problems", "learner_notes")
