"""Typed contracts for each agent. Graph state stores these as JSON-safe dictionaries.

Facts come from the runner, tests or AST analysis. Inferences are separate and carry a confidence.
Unknown stays None: nothing here forces an estimate to exist.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["low", "moderate", "high"]
Trend = Literal["improving", "steady", "stalled", "regressing", "solved", "unknown"]
Category = Literal[
    "accepted", "syntax", "runtime", "timeout", "memory", "output_limit", "wrong_answer",
    "partial", "missing_function", "no_attempt", "no_tests", "service_failure", "cancelled",
]


class Fact(BaseModel):
    kind: str
    text: str
    line: int | None = None
    source: Literal["runner", "tests", "code_analysis"]


class Inference(BaseModel):
    misconception: str
    confidence: Literal["low", "medium", "high"]
    evidence: list[str] = Field(default_factory=list)
    source: Literal["rules", "llm"] = "rules"


class DiagnosticOutput(BaseModel):
    category: Category
    issue_key: str
    title: str
    student_summary: str
    facts: list[Fact] = Field(default_factory=list)
    inferences: list[Inference] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    affected_lines: list[int] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertain: bool = False
    repeat_count: int = 1
    tests_passed: int = 0
    tests_total: int = 0
    source: Literal["rules", "rules+llm"] = "rules"


class MasteryEstimate(BaseModel):
    value: float
    low: float
    high: float
    band: Literal["not_enough_evidence", "starting", "developing", "proficient", "strong"]
    evidence_weight: float
    updated: bool
    explanation: str


class CognitiveOutput(BaseModel):
    unit_id: str
    mastery: MasteryEstimate
    confidence: float | None = None
    confidence_basis: str | None = None
    confusion: Level | None = None
    confusion_evidence: list[str] = Field(default_factory=list)
    cognitive_load: Level | None = None
    load_evidence: list[str] = Field(default_factory=list)
    progress: Trend = "unknown"
    progress_evidence: list[str] = Field(default_factory=list)
    best_ratio: float | None = None
    graded_attempts_on_problem: int = 0
    state_version: int = 0
    method_version: str = "cs-1.0"
    timestamp: str = ""


class RetrievalOutput(BaseModel):
    reliable: bool
    reason: str
    candidates_considered: int = 0
    suggested_level: int | None = None
    suggested_strategy: str | None = None
    effectiveness: float | None = None
    support: int = 0
    provenance: Literal["live", "synthetic", "mixed"] | None = None
    mean_similarity: float | None = None
    vector_version: str = "sv-1"
    evidence: list[dict] = Field(default_factory=list)


class Presentation(BaseModel):
    format: Literal["none", "question", "hint", "outline", "example"] = "none"
    max_sentences: int = 3
    max_words: int = 90
    allow_code: Literal["none", "analogous_only"] = "none"
    one_action: bool = False


class DSDADecision(BaseModel):
    action: Literal["give_help", "offer_help", "wait", "none"]
    level: int = Field(ge=0, le=4)
    level_name: str
    strategy: str
    focus_issue: str
    timing: Literal["show_now", "offer", "wait_for_learner", "not_needed"]
    presentation: Presentation
    reason_codes: list[str]
    reason_student: str
    score: float | None = None
    score_components: dict[str, float] = Field(default_factory=dict)
    used_retrieval: bool = False
    policy_version: str


class HintDraft(BaseModel):
    text: str
    source: Literal["ai", "built_in"]
    built_in_reason: str | None = None
    attempts: int = 1
    violations: list[str] = Field(default_factory=list)


class ReflectionOutput(BaseModel):
    action: Literal["ask", "defer", "skip"]
    prompt: str | None = None
    reason: str
    source: Literal["ai", "built_in"] = "built_in"


class PlanOutput(BaseModel):
    action: Literal[
        "continue_current", "practise_prerequisite", "similar_independent",
        "harder_next", "review_concept", "start_path",
    ]
    title: str
    reason: str
    reason_codes: list[str]
    problem_id: str | None = None
    problem_title: str | None = None
    unit_id: str | None = None
    unit_title: str | None = None
    keep_current_active: bool = True
    alternatives: list[dict] = Field(default_factory=list)
