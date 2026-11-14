"""Typed contracts for each agent. Graph state stores these as JSON-safe dictionaries.

Facts come from the runner, tests or AST analysis. Inferences are separate and carry a confidence.
Unknown stays None: nothing here forces an estimate to exist.
"""
from __future__ import annotations

from typing import Any, Literal

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


class FailingExample(BaseModel):
    """A failing test the learner may see. Hidden tests never appear here."""

    input: str
    got: str | None = None
    expected: str | None = None


class HintEvidence(BaseModel):
    """Exact, observed details that let help be specific. Everything here is safe to show the learner."""

    error_type: str | None = None
    message: str | None = None
    line: int | None = None
    column: int | None = None
    source_line: str | None = None
    token: str | None = None
    previous_token: str | None = None
    failing_example: FailingExample | None = None
    probe_line: int | None = None  # a useful place to look, when no error names one
    probe_names: list[str] = Field(default_factory=list)
    probe_inside_loop: bool = False  # print as the first line inside the loop that starts on probe_line
    # The learner's main loop, so logic hints can point at their own code rather than talk about loops in general.
    loop_line: int | None = None
    loop_source: str | None = None
    loop_variable: str | None = None
    result_name: str | None = None  # the name the loop builds up, when it is set before the loop


class AttemptComparison(BaseModel):
    """How this code version relates to the previous one. Facts only, no judgement of the learner."""

    has_previous: bool = False
    previous_snapshot_id: str | None = None
    code_changed: bool = False
    changed_lines: list[int] = Field(default_factory=list)
    previous_issue_key: str | None = None
    same_issue: bool = False
    issue_changed: bool = False
    # Moved from a stage that stops earlier (syntax) to one that gets further (runs, then partly passes).
    moved_further: bool = False
    moved_back: bool = False
    same_measure: bool = False
    previous_passed: int | None = None
    previous_total: int | None = None
    tests_delta: int | None = None


class LearnerQuestion(BaseModel):
    """What the learner typed, read as data. It selects a kind of answer and cannot change the policy."""

    text: str = ""
    intent: str = "general"
    concept: str | None = None
    stuck: bool = False


class TraceRow(BaseModel):
    name: str
    values: list[str]
    more: bool = False


class FocusContext(BaseModel):
    """The part of the code the learner pointed at, with what was observed there."""

    start: int
    end: int
    lines: list[str] = Field(default_factory=list)
    kinds: list[str] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)
    auto: bool = False  # chosen by the tutor, because the learner did not point at anything
    contains_error: bool = False
    error_elsewhere: bool = False
    trace: list[TraceRow] = Field(default_factory=list)
    trace_runs: int = 0
    trace_input: str | None = None
    trace_never_ran: bool = False
    params: list[str] = Field(default_factory=list)  # the function's parameters, which a loop usually leaves alone


class ErrorDiagnosis(BaseModel):
    """What went wrong and why, as far as the evidence shows. `explanation` and `evidence` are safe to show at any time."""

    error_class: Literal["syntax", "name_resolution", "type", "runtime", "logic", "timeout", "output_mismatch", "none"]
    cause: str
    likely_cause: str
    concept: str
    location: int | None = None  # only when it was reliably identified
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    explanation: str = ""
    name: str | None = None
    suggestion: str | None = None
    module: str | None = None
    variant: str | None = None
    call: str | None = None
    args: list[str] = Field(default_factory=list)
    receiver: str | None = None
    owner: str | None = None
    form: str | None = None
    purpose: str | None = None
    where: str | None = None
    defined_at: int | None = None
    target: str | None = None
    goal: str | None = None
    goal_kind: str | None = None
    known: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


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
    evidence: HintEvidence = Field(default_factory=HintEvidence)
    comparison: AttemptComparison = Field(default_factory=AttemptComparison)
    question: LearnerQuestion | None = None
    focus: FocusContext | None = None
    technique: str | None = None  # what this problem practises, from the topic's lesson
    diagnosis: ErrorDiagnosis | None = None
    technique_example: dict[str, str] | None = None  # a lesson example of the same technique, on a different task
    observed: bool = False  # focus and trace were added by the tutor to explain a wrong answer, not asked for


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
    # Approaches this learner already tried here without progress are not suggested again.
    excluded_strategies: list[str] = Field(default_factory=list)


class Presentation(BaseModel):
    format: Literal["none", "question", "hint", "outline", "example"] = "none"
    max_sentences: int = 3
    max_words: int = 90
    allow_code: Literal["none", "analogous_only"] = "none"
    one_action_at_a_time: bool = False


class SolutionConstraints(BaseModel):
    # A literal, so no configuration, model reply or code path can ever turn this on.
    allow_complete_solution: Literal[False] = False
    allow_analogous_example: bool = False


class DSDADecision(BaseModel):
    """The DSDA contract. The model may word a hint, but nothing here can be changed by it."""

    support_need_score: float = 0.0
    selected_level: int = Field(ge=0, le=4)
    level_name: str
    strategy: str
    reason_codes: list[str]
    reason_student: str
    evidence: dict = Field(default_factory=dict)
    presentation: Presentation
    constraints: SolutionConstraints = Field(default_factory=SolutionConstraints)
    await_learner_action: Literal[True] = True
    policy_version: str
    action: Literal["give_help", "offer_help", "wait", "none"]
    focus_issue: str
    timing: Literal["show_now", "offer", "wait_for_learner", "not_needed"]
    theme: str = "default"
    score_components: dict[str, float] = Field(default_factory=dict)
    used_retrieval: bool = False


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
    kind: str | None = None  # which question was asked, so the reply to the answer knows what to listen for
    context: dict[str, Any] = Field(default_factory=dict)  # the issue, technique and the learner's own names, for that reply


class ReflectionReply(BaseModel):
    """The tutor's reply to a reflection answer. Never a grade, and never the fix for an unsolved problem."""

    quality: Literal["specific", "partial", "unsure", "brief"]
    feedback: str
    matched: list[str] = Field(default_factory=list)  # the key ideas the answer named


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
    route: list[dict] = Field(default_factory=list)  # where the learner is now, then up to three topics ahead
