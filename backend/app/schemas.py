"""Typed API contracts. The frontend's TypeScript types are generated from these via OpenAPI."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


# ---- auth and users
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "teacher"] = "student"
    invite_code: str | None = Field(default=None, max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class DemoIn(BaseModel):
    role: Literal["student", "teacher"] = "student"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_demo: bool
    experience_level: str | None
    goal: str | None
    onboarding_completed: bool
    research_consent: bool
    preferences: dict[str, Any]


class OnboardingIn(BaseModel):
    experience_level: Literal["new", "some", "intermediate", "advanced"]
    goal: Literal["basics", "course", "dsa", "explore"]
    research_consent: bool = False
    skip_walkthroughs: bool = False


class PreferencesIn(BaseModel):
    preferences: dict[str, Any] = Field(max_length=40)


class StatusOut(BaseModel):
    execution: dict[str, Any]
    tutor_model: dict[str, Any]
    demo_mode: bool
    environment: str
    languages: list[str]


class ClassJoinIn(BaseModel):
    join_code: str = Field(min_length=4, max_length=16)


class ClassCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class ClassOut(BaseModel):
    id: str
    name: str
    join_code: str | None = None
    is_synthetic: bool = False
    members: int | None = None


# ---- content
class ProblemSummary(BaseModel):
    id: str
    title: str
    unit_id: str
    unit_title: str
    difficulty: str | None
    concepts: list[str]
    languages: list[str]
    status: Literal["not_started", "in_progress", "solved"]
    source_type: str
    source_name: str | None
    is_mine: bool
    recommended_first: bool = False


class ExampleOut(BaseModel):
    name: str
    input: str
    expected: str | None
    origin: str


class ProblemDetail(BaseModel):
    id: str
    title: str
    unit_id: str
    unit_title: str
    difficulty: str | None
    concepts: list[str]
    languages: list[str]
    mode: str
    description: str
    constraints: str | None
    input_format: str | None
    output_format: str | None
    starter_code: str
    function_name: str | None
    prelude: str | None
    per_test_seconds: float
    examples: list[ExampleOut]
    hidden_test_count: int
    source_type: str
    source_name: str | None
    source_url: str | None
    source_note: str | None
    source_retrieved_at: datetime | None
    is_mine: bool


class LessonOut(BaseModel):
    title: str
    objective: str | None = None
    explanation: str
    examples: list[dict[str, Any]] = Field(default_factory=list)


class UnitPathItem(BaseModel):
    id: str
    title: str
    order: int
    track: str
    optional: bool
    summary: str
    prerequisites: list[str]
    problems_total: int
    problems_solved: int
    state: Literal["completed", "recommended", "in_progress", "available", "needs_foundations"]
    band: str
    mastery_low: float | None
    mastery_high: float | None
    evidence_note: str


class PathOut(BaseModel):
    units: list[UnitPathItem]
    recommendation: dict[str, Any]
    current_unit_id: str | None


class UnitDetail(BaseModel):
    id: str
    title: str
    summary: str
    track: str
    optional: bool
    prerequisites: list[dict[str, str]]
    lessons: list[LessonOut]
    problems: list[ProblemSummary]


# ---- workspace
class RunIn(BaseModel):
    code: str = Field(max_length=100000)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    custom_args: str | None = Field(default=None, max_length=20000, description="A JSON array of arguments")
    custom_stdin: str | None = Field(default=None, max_length=20000)


class SubmitIn(BaseModel):
    code: str = Field(max_length=100000)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    active_seconds: int | None = Field(default=None, ge=0, le=86400)
    self_confidence: Literal["low", "medium", "high"] | None = None
    self_state: Literal["stuck", "overwhelmed", "fine"] | None = None


class HintIn(SubmitIn):
    request_size: Literal["nudge", "more"] | None = None
    question: str | None = Field(default=None, max_length=500)


class EvaluationOut(BaseModel):
    id: str
    kind: str
    status: str
    verdict: str | None
    passed: int
    total: int
    results: list[dict[str, Any]]
    message: str | None
    snapshot_id: str
    code: str
    runner_backend: str | None
    runner_secure: bool | None
    duration_ms: int | None
    created_at: datetime
    finished_at: datetime | None


class StageOut(BaseModel):
    stage: str
    agent: str | None
    status: str
    reason: str | None
    duration_ms: int | None


class RunOut(BaseModel):
    id: str
    trigger: str
    status: str
    problem_id: str
    snapshot_id: str
    evaluation_id: str | None
    correlation_id: str
    code: str
    stages: list[StageOut]
    response: dict[str, Any] | None
    evaluation: EvaluationOut | None
    created_at: datetime
    finished_at: datetime | None


class Accepted(BaseModel):
    id: str
    created: bool


class DraftIn(BaseModel):
    code: str = Field(max_length=100000)
    base_version: int | None = None


class DraftOut(BaseModel):
    code: str
    version: int
    updated_at: datetime


class HintRow(BaseModel):
    id: str
    level: int
    level_name: str
    text: str
    why: str
    source: str
    requested: bool
    outcome: str | None
    helpful: bool | None
    problem_id: str
    problem_title: str | None = None
    created_at: datetime


class WorkspaceOut(BaseModel):
    problem: ProblemDetail
    draft: DraftOut | None
    latest_run: RunOut | None
    latest_evaluation: EvaluationOut | None
    pending_reflection: dict[str, Any] | None
    hints: list[HintRow]
    active_seconds: int
    solved: bool


class ReflectionAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class HintFeedbackIn(BaseModel):
    helpful: bool


class SurveyIn(BaseModel):
    usefulness: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    hint_adequacy: int = Field(ge=1, le=5)
    adaptivity: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class AssessmentOut(BaseModel):
    phase: str
    title: str
    note: str
    questions: list[dict[str, Any]]
    completed: bool
    score: int | None
    max_score: int | None


class AssessmentSubmitIn(BaseModel):
    answers: dict[str, str] = Field(max_length=40)


# ---- imports
class ParseIn(BaseModel):
    text: str = Field(min_length=20, max_length=30000)


class LookupIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class ImportExample(BaseModel):
    input_text: str = ""
    output_text: str = ""
    args: list[Any] | None = None
    expected: Any | None = None
    stdin: str | None = None
    expected_stdout: str | None = None
    parsed: bool = False


class ImportDraft(BaseModel):
    title: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=20000)
    constraints: str | None = Field(default=None, max_length=4000)
    input_format: str | None = Field(default=None, max_length=4000)
    output_format: str | None = Field(default=None, max_length=4000)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    unit_id: str | None = None
    mode: Literal["function", "stdio"] = "function"
    function_name: str | None = Field(default=None, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    parameters: list[str] = Field(default_factory=list, max_length=12)
    starter_code: str | None = Field(default=None, max_length=8000)
    examples: list[ImportExample] = Field(default_factory=list, max_length=20)
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    source_retrieved_at: datetime | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LookupOut(BaseModel):
    supported: bool
    source_name: str | None
    message: str
    guidance: str | None = None
    draft: ImportDraft | None = None


class TestCase(BaseModel):
    id: str | None = None
    label: str | None = Field(default=None, max_length=160)
    origin: Literal["example", "provided", "generated", "learner"] = "learner"
    category: str | None = Field(default=None, max_length=24)
    kind: Literal["args", "stdio"] = "args"
    args: list[Any] | None = None
    stdin: str | None = Field(default=None, max_length=300000)
    expected: Any | None = None
    compare: Literal["exact", "unordered", "completes"] = "exact"
    needs_expected: bool = False
    enabled: bool = True
    expected_source: str | None = Field(default=None, max_length=32)


class GenerateTestsIn(BaseModel):
    draft: ImportDraft


class TestsOut(BaseModel):
    tests: list[TestCase]
    notes: list[str]


class SaveImportIn(BaseModel):
    draft: ImportDraft
    tests: list[TestCase] = Field(max_length=60)


class ImportOut(BaseModel):
    id: str
    draft: ImportDraft
    tests: list[TestCase]


class UnitOption(BaseModel):
    id: str
    title: str
