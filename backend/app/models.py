"""Relational schema (PostgreSQL). Vectors live in ChromaDB and join back here by id.

Provenance is explicit: `intervention_cases.provenance` and `users.is_synthetic` keep
synthetic demonstration records apart from real learner data everywhere they are queried.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


ID = String(32)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="student")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    experience_level: Mapped[str | None] = mapped_column(String(24))
    goal: Mapped[str | None] = mapped_column(String(32))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    research_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    thread_epoch: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Unit(Base):
    __tablename__ = "units"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    order_index: Mapped[int] = mapped_column(Integer)
    track: Mapped[str] = mapped_column(String(24))
    summary: Mapped[str] = mapped_column(Text)
    optional: Mapped[bool] = mapped_column(Boolean, default=False)
    prerequisites: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    lessons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    guide: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"), index=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), index=True)
    difficulty_score: Mapped[float] = mapped_column(Float, default=0.5)
    concepts: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    language: Mapped[str] = mapped_column(String(16), default="python")
    mode: Mapped[str] = mapped_column(String(16), default="function")
    description: Mapped[str] = mapped_column(Text)
    constraints: Mapped[str | None] = mapped_column(Text)
    input_format: Mapped[str | None] = mapped_column(Text)
    output_format: Mapped[str | None] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text)
    function_name: Mapped[str | None] = mapped_column(String(120))
    prelude: Mapped[str | None] = mapped_column(Text)
    per_test_seconds: Mapped[float] = mapped_column(Float, default=2.0)
    source_type: Mapped[str] = mapped_column(String(24), default="curriculum")
    source_name: Mapped[str | None] = mapped_column(String(160))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_note: Mapped[str | None] = mapped_column(Text)
    source_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    learner_notes: Mapped[str | None] = mapped_column(Text)
    pattern: Mapped[str | None] = mapped_column(String(64))
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recommended_first: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tests: Mapped[list[ProblemTest]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="ProblemTest.order_index"
    )


class ProblemTest(Base):
    """`expected` is the assessment answer. It never reaches clients for hidden tests or the sandbox at all."""

    __tablename__ = "problem_tests"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    visibility: Mapped[str] = mapped_column(String(12), default="hidden")
    origin: Mapped[str] = mapped_column(String(24), default="curriculum")
    category: Mapped[str | None] = mapped_column(String(24))
    label: Mapped[str | None] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(12))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    expected: Mapped[Any] = mapped_column(JSONB, nullable=True)
    compare: Mapped[str] = mapped_column(String(16), default="exact")
    needs_expected: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    problem: Mapped[Problem] = relationship(back_populates="tests")


class ProblemSolution(Base):
    """Reference solutions: server-side only, for test verification and leak detection."""

    __tablename__ = "problem_solutions"
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    code: Mapped[str] = mapped_column(Text)


class Draft(Base):
    __tablename__ = "drafts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True, default="python")
    code: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CodeSnapshot(Base):
    __tablename__ = "code_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", "code_hash", name="uq_snapshot_code"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(Text)
    code_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Evaluation(Base):
    """One execution of one snapshot. `kind` separates Run, Submit and hint evidence probes."""

    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_evaluation_idempotency"),
        Index("ix_evaluation_user_problem_time", "user_id", "problem_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("code_snapshots.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(12))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    verdict: Mapped[str | None] = mapped_column(String(24))
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    custom_input: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    public_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    internal_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    message: Mapped[str | None] = mapped_column(Text)
    runner_backend: Mapped[str | None] = mapped_column(String(32))
    runner_secure: Mapped[bool | None] = mapped_column(Boolean)
    active_seconds: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_run_idempotency"),
        Index("ix_run_user_problem_time", "user_id", "problem_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    evaluation_id: Mapped[str | None] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("code_snapshots.id", ondelete="CASCADE"))
    trigger: Mapped[str] = mapped_column(String(24))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(32))
    thread_id: Mapped[str] = mapped_column(String(128))
    cycle: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    policy_version: Mapped[str | None] = mapped_column(String(32))
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentStep.sequence"
    )


class AgentStep(Base):
    """Observability: what ran, what was skipped or failed and why. These records drive the real progress UI."""

    __tablename__ = "agent_steps"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(32))
    agent: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text)
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    llm: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[PipelineRun] = relationship(back_populates="steps")


class Diagnostic(Base):
    __tablename__ = "diagnostics"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(24))
    issue_key: Mapped[str] = mapped_column(String(64))
    repeat_count: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TopicState(Base):
    __tablename__ = "learner_topic_state"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"), primary_key=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.2)
    evidence_weight: Mapped[float] = mapped_column(Float, default=0.0)
    graded_attempts: Mapped[int] = mapped_column(Integer, default=0)
    solved_count: Mapped[int] = mapped_column(Integer, default=0)
    independent_solved: Mapped[int] = mapped_column(Integer, default=0)
    assisted_solved: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StateSnapshot(Base):
    """Versioned history of estimates. Unknown values stay NULL rather than being guessed."""

    __tablename__ = "learner_state_snapshots"
    __table_args__ = (Index("ix_state_user_time", "user_id", "created_at"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    method_version: Mapped[str] = mapped_column(String(24))
    mastery: Mapped[float] = mapped_column(Float)
    mastery_low: Mapped[float] = mapped_column(Float)
    mastery_high: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    confusion: Mapped[str | None] = mapped_column(String(12))
    cognitive_load: Mapped[str | None] = mapped_column(String(12))
    progress: Mapped[str | None] = mapped_column(String(16))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Hint(Base):
    __tablename__ = "hints"
    __table_args__ = (Index("ix_hint_user_problem_time", "user_id", "problem_id", "created_at"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("code_snapshots.id", ondelete="CASCADE"))
    issue_key: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(24))
    level: Mapped[int] = mapped_column(Integer)
    strategy: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(24))
    requested: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery: Mapped[str] = mapped_column(String(12), default="shown")
    reason_student: Mapped[str] = mapped_column(Text)
    reason_codes: Mapped[list[str]] = mapped_column(ARRAY(String(48)), default=list)
    policy_version: Mapped[str] = mapped_column(String(32))
    score: Mapped[float | None] = mapped_column(Float)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    baseline_passed: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str | None] = mapped_column(String(16))
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    helpful: Mapped[bool | None] = mapped_column(Boolean)
    learner_request: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InteractionRecord(Base):
    """One row per completed learning cycle: what was seen, what each agent concluded, and what was decided.

    This is the persistent interaction state the agents read back on the next cycle. It holds no hidden
    test contents, no reference solutions, and no prompts.
    """

    __tablename__ = "interaction_records"
    __table_args__ = (Index("ix_interaction_user_problem_time", "user_id", "problem_id", "created_at"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("code_snapshots.id", ondelete="CASCADE"))
    evaluation_id: Mapped[str | None] = mapped_column(ForeignKey("evaluations.id", ondelete="SET NULL"))
    evaluation_kind: Mapped[str | None] = mapped_column(String(12))
    trigger: Mapped[str] = mapped_column(String(24))
    verdict: Mapped[str | None] = mapped_column(String(24))
    category: Mapped[str] = mapped_column(String(24))
    issue_key: Mapped[str] = mapped_column(String(64))
    tests_passed: Mapped[int] = mapped_column(Integer, default=0)
    tests_total: Mapped[int] = mapped_column(Integer, default=0)
    code_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    learner_input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    diagnostic: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cognitive: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    retrieval: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    hint_id: Mapped[str | None] = mapped_column(ForeignKey("hints.id", ondelete="SET NULL"))
    active_seconds: Mapped[int | None] = mapped_column(Integer)
    policy_version: Mapped[str | None] = mapped_column(String(32))
    # The reasoning trail: raw error, prior hints, the hint generated and whether validation passed.
    reasoning: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    # Filled in by the next cycle on this problem.
    next_action: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    resolved: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Reflection(Base):
    __tablename__ = "reflections"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="prompted")
    answer: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str | None] = mapped_column(String(40))
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    feedback: Mapped[str | None] = mapped_column(Text)
    quality: Mapped[str | None] = mapped_column(String(16))


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    problem_id: Mapped[str | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"))
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"))
    title: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    reason_codes: Mapped[list[str]] = mapped_column(ARRAY(String(48)), default=list)
    alternatives: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearnerEvent(Base):
    """Minimal append-only log. Holds no keystroke content."""

    __tablename__ = "learner_events"
    __table_args__ = (Index("ix_event_user_time", "user_id", "created_at"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    problem_id: Mapped[str | None] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InterventionCase(Base):
    """A past situation, the help given and the outcome. Anonymous: no user id, no code, no problem text.

    provenance: 'live' = measured on this platform. 'synthetic' = generated demonstration data.
    Only 'live' may be reported as evidence.
    """

    __tablename__ = "intervention_cases"
    __table_args__ = (UniqueConstraint("source_hint_hash", name="uq_case_source_hint"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    provenance: Mapped[str] = mapped_column(String(16), index=True)
    source_hint_hash: Mapped[str | None] = mapped_column(String(64))
    owner_hash: Mapped[str | None] = mapped_column(String(64))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    category: Mapped[str] = mapped_column(String(24))
    issue_key: Mapped[str] = mapped_column(String(64))
    difficulty: Mapped[float] = mapped_column(Float)
    level: Mapped[int] = mapped_column(Integer)
    strategy: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[str] = mapped_column(String(16))
    vector: Mapped[list[float]] = mapped_column(ARRAY(Float))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DatasetProblemStat(Base):
    """Aggregates computed from a programming dataset such as CodeNet. Not tutoring evidence."""

    __tablename__ = "dataset_problem_stats"
    dataset: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_problem_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    language: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    rating: Mapped[float | None] = mapped_column(Float)
    submissions: Mapped[int] = mapped_column(Integer, default=0)
    learners: Mapped[int] = mapped_column(Integer, default=0)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    first_attempt_acceptance: Mapped[float | None] = mapped_column(Float)
    mean_attempts_to_accept: Mapped[float | None] = mapped_column(Float)
    status_counts: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    provenance_note: Mapped[str] = mapped_column(Text)


class Classroom(Base):
    __tablename__ = "classrooms"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    join_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ClassMember(Base):
    __tablename__ = "class_members"
    class_id: Mapped[str] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssessmentAttempt(Base):
    """Pre and post knowledge checks: the only source for learning gain."""

    __tablename__ = "assessment_attempts"
    __table_args__ = (UniqueConstraint("user_id", "phase", name="uq_assessment_phase"),)
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(8))
    score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    usefulness: Mapped[int] = mapped_column(Integer)
    clarity: Mapped[int] = mapped_column(Integer)
    hint_adequacy: Mapped[int] = mapped_column(Integer)
    adaptivity: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
