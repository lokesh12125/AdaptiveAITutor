"""Graph nodes. Each one wraps an agent with its persistence boundary and step recording.

Agents are plain functions over typed inputs. Nodes load what those agents need, record what happened,
and fall back safely: one stage failing never loses the learner's code or blocks the rest of the cycle.
All learner-state writes happen together in `finalize`.
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from ..db import session_scope
from ..models import (
    AgentStep,
    CodeSnapshot,
    Diagnostic,
    Evaluation,
    Hint,
    InterventionCase,
    LearnerEvent,
    PipelineRun,
    Problem,
    ProblemSolution,
    Recommendation,
    Reflection,
    StateSnapshot,
    TopicState,
    Unit,
    User,
)
from . import cognitive as cognitive_agent
from . import compose
from . import dsda as dsda_agent
from . import hints as hint_agent
from . import planner as planner_agent
from . import reflection as reflection_agent
from . import retrieval as retrieval_agent
from .contracts import DiagnosticOutput, DSDADecision, Fact
from .diagnostic import ISSUE_TITLES, run_diagnostic
from .llm import LLMUnavailable, gateway

log = logging.getLogger("csmasf.pipeline")

AGENT_STAGES = [
    ("diagnostic", "diagnostic"),
    ("cognitive_state", "cognitive_state"),
    ("retrieval", "similar_learner_retrieval"),
    ("dsda", "adaptive_scaffolding"),
    ("generate_hint", "adaptive_scaffolding"),
    ("validate_hint", "adaptive_scaffolding"),
    ("reflection", "reflection"),
    ("planner", "learning_planner"),
]


class StepRecord:
    def __init__(self) -> None:
        self.status = "completed"
        self.reason: str | None = None
        self.output: dict[str, Any] | None = None
        self.llm: dict[str, Any] | None = None
        self.error: str | None = None
        self.retries = 0


def is_graded(state: dict[str, Any]) -> bool:
    """A hint may reuse evidence from a graded run, but the hint itself is never a graded attempt."""
    return state["event"]["trigger"] == "submission" and state["evaluation"].get("kind") == "submit"


def _next_sequence(db, run_id: str) -> int:
    return (db.scalar(select(func.count()).select_from(AgentStep).where(AgentStep.run_id == run_id)) or 0) + 1


@contextmanager
def step(state: dict[str, Any], stage: str, agent: str | None, input_summary: dict[str, Any] | None = None):
    run_id = state["event"]["run_id"]
    with session_scope() as db:
        row = AgentStep(run_id=run_id, sequence=_next_sequence(db, run_id), stage=stage, agent=agent, status="running", input_summary=input_summary)
        db.add(row)
        db.flush()
        step_id = row.id
    record = StepRecord()
    started = time.monotonic()
    try:
        yield record
    except Exception as exc:  # noqa: BLE001 - recorded, then handled by `guarded`
        record.status, record.error = "failed", f"{type(exc).__name__}: {str(exc)[:300]}"
        log.exception("stage %s failed (correlation %s)", stage, state["event"].get("correlation_id"))
        raise
    finally:
        with session_scope() as db:
            row = db.get(AgentStep, step_id)
            row.status, row.reason, row.output_summary, row.llm, row.error, row.retries = (
                record.status, record.reason, record.output, record.llm, record.error, record.retries,
            )
            row.duration_ms = int((time.monotonic() - started) * 1000)


def record_skip(state: dict[str, Any], stage: str, agent: str | None, reason: str) -> None:
    run_id = state["event"]["run_id"]
    with session_scope() as db:
        db.add(AgentStep(run_id=run_id, sequence=_next_sequence(db, run_id), stage=stage, agent=agent, status="skipped", reason=reason, duration_ms=0))


def guarded(stage: str, agent: str | None, fallback: Callable[[dict[str, Any]], dict[str, Any]]):
    """Run a node body inside step recording. On failure, use a safe fallback and carry on."""

    def wrap(body: Callable[[dict[str, Any], StepRecord], dict[str, Any]]):
        def node(state: dict[str, Any]) -> dict[str, Any]:
            try:
                with step(state, stage, agent) as record:
                    return body(state, record)
            except Exception:  # noqa: BLE001
                return fallback(state)

        node.__name__ = stage
        return node

    return wrap


# ---------------------------------------------------------------- intake and evaluation

def intake(state: dict[str, Any]) -> dict[str, Any]:
    event = state["event"]
    with step(state, "intake", None, {"trigger": event["trigger"]}) as record:
        with session_scope() as db:
            problem = db.get(Problem, event["problem_id"])
            user = db.get(User, event["user_id"])
            context = {
                "problem": {
                    "id": problem.id, "title": problem.title, "description": problem.description,
                    "unit_id": problem.unit_id, "difficulty": problem.difficulty, "difficulty_score": problem.difficulty_score,
                    "concepts": problem.concepts, "function_name": problem.function_name, "source_type": problem.source_type,
                },
                "preferences": user.preferences or {},
                "goal": user.goal, "experience": user.experience_level, "is_demo": user.is_demo, "is_synthetic": user.is_synthetic,
            }
        record.output = {"cycle": state.get("cycle", 0)}
    return {"context": context, "generation_attempts": 0, "violations": [], "hint": None}


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    from .service import run_evaluation

    event = state["event"]
    with step(state, "evaluate", None, {"evaluation_id": event["evaluation_id"]}) as record:
        result = run_evaluation(event["evaluation_id"])
        record.output = {"verdict": result["verdict"], "passed": result["passed"], "total": result["total"], "backend": result.get("backend"), "reused": result.get("reused", False)}
        if result["verdict"] == "service_failure":
            record.status = "failed"
            record.reason = "The execution service was unavailable. This is not related to the learner's code."
        elif result["verdict"] == "cancelled":
            record.status = "skipped"
            record.reason = "Cancelled by the learner."
        elif result.get("reused"):
            record.reason = "Used the existing result for this exact code."
    return {"evaluation": result}


# ---------------------------------------------------------------- diagnostic

def _diagnostic_fallback(state: dict[str, Any]) -> dict[str, Any]:
    evaluation = state["evaluation"]
    category = {"accepted": "accepted", "syntax_error": "syntax", "runtime_error": "runtime", "timeout": "timeout"}.get(evaluation.get("verdict"), "wrong_answer")
    output = DiagnosticOutput(
        category=category, issue_key=f"{category}:general", title=ISSUE_TITLES.get(category, "Result"),
        student_summary=f"{evaluation.get('passed', 0)} of {evaluation.get('total', 0)} tests passed.",
        confidence=0.2, uncertain=True, tests_passed=evaluation.get("passed", 0), tests_total=evaluation.get("total", 0),
    )
    return {"diagnostic": output.model_dump()}


@guarded("diagnostic", "diagnostic", _diagnostic_fallback)
def diagnostic(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, problem, evaluation = state["event"], state["context"]["problem"], state["evaluation"]
    with session_scope() as db:
        row = db.get(Evaluation, evaluation["id"])
        internal = row.internal_results
        snapshot = db.get(CodeSnapshot, row.snapshot_id)
        code = snapshot.code
        previous = db.execute(
            select(Diagnostic.issue_key, PipelineRun.snapshot_id)
            .join(PipelineRun, PipelineRun.id == Diagnostic.run_id)
            .where(Diagnostic.user_id == event["user_id"], Diagnostic.problem_id == event["problem_id"])
            .order_by(Diagnostic.created_at.desc()).limit(8)
        ).all()
    # Asking again about the same code is not a new occurrence of the issue.
    previous_keys = [issue for issue, snapshot_id in previous if snapshot_id != event["snapshot_id"]]

    verdict = evaluation["verdict"]
    if verdict == "public_passed":
        passed, total = evaluation["passed"], evaluation["total"]
        output = DiagnosticOutput(
            category="partial", issue_key="logic:public_examples_pass", title="Your code passes the visible examples",
            student_summary=f"All {total} visible examples pass. Submitting checks your code on further tests too.",
            facts=[Fact(kind="public_passed", source="tests", text=f"{passed} of {total} visible examples pass.")],
            concepts=problem.get("concepts", []), confidence=0.8, tests_passed=passed, tests_total=total,
        )
        llm_meta = None
    else:
        output, llm_meta = run_diagnostic(verdict, internal, code, problem, previous_keys)
    record.llm = llm_meta
    record.output = {"category": output.category, "issue_key": output.issue_key, "confidence": output.confidence, "repeat_count": output.repeat_count, "facts": len(output.facts)}
    return {"diagnostic": output.model_dump()}


# ---------------------------------------------------------------- cognitive state

def _resolve_hint_outcomes(db, event: dict[str, Any], evaluation: dict[str, Any], diag: dict[str, Any]) -> int:
    """Decide whether earlier hints were followed by progress. Requires changed code as evidence."""
    pending = db.scalars(
        select(Hint).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.outcome.is_(None), Hint.delivery == "shown", Hint.snapshot_id != event["snapshot_id"])
    ).all()
    if not pending:
        return 0
    total = evaluation.get("total") or 0
    ratio = (evaluation.get("passed") or 0) / total if total else 0.0
    solved = diag["category"] == "accepted"
    now = datetime.now(UTC)
    for hint in pending:
        baseline = (hint.validation or {}).get("baseline_ratio")
        same_measure = (hint.validation or {}).get("baseline_kind") == evaluation.get("kind")
        if solved:
            outcome = "solved"
        elif same_measure and baseline is not None and ratio > baseline:
            outcome = "progress"
        elif diag["issue_key"] != hint.issue_key and not (same_measure and baseline is not None and ratio < baseline):
            outcome = "progress"
        else:
            outcome = "no_progress"
        hint.outcome, hint.outcome_at = outcome, now
        _store_live_case(db, hint, event)
    return len(pending)


def _store_live_case(db, hint: Hint, event: dict[str, Any]) -> None:
    """Pool a resolved hint anonymously, only if this learner allows it and is a real account."""
    user = db.get(User, event["user_id"])
    vector = (hint.validation or {}).get("query_vector")
    if not vector or user.is_demo or user.is_synthetic or (user.preferences or {}).get("share_anonymous_outcomes") is False:
        return
    problem = db.get(Problem, hint.problem_id)
    case = InterventionCase(
        provenance="live", source_hint_hash=hashlib.sha256(hint.id.encode()).hexdigest(), owner_hash=retrieval_agent.anonymise(user.id),
        unit_id=hint.unit_id, category=retrieval_agent.category_group(hint.category), issue_key=hint.issue_key,
        difficulty=problem.difficulty_score, level=hint.level, strategy=hint.strategy, outcome=hint.outcome, vector=vector,
    )
    db.add(case)
    db.flush()
    try:
        retrieval_agent.store.upsert_case(case)
    except Exception as exc:  # noqa: BLE001 - the relational record is kept; the vector can be reindexed
        log.warning("could not index case: %s", type(exc).__name__)


def _load_cognitive_input(db, event: dict[str, Any], problem: dict[str, Any], evaluation: dict[str, Any], diag: dict[str, Any], graded: bool) -> cognitive_agent.CognitiveInput:
    unit_id = problem["unit_id"]
    topic = db.get(TopicState, (event["user_id"], unit_id))
    graded_rows = db.execute(
        select(Evaluation, Diagnostic.issue_key)
        .outerjoin(PipelineRun, PipelineRun.evaluation_id == Evaluation.id)
        .outerjoin(Diagnostic, Diagnostic.run_id == PipelineRun.id)
        .where(Evaluation.user_id == event["user_id"], Evaluation.problem_id == event["problem_id"], Evaluation.kind == "submit",
               Evaluation.status == "completed", Evaluation.id != evaluation["id"], Evaluation.verdict.notin_(["service_failure", "cancelled"]))
        .order_by(Evaluation.created_at)
    ).all()
    last_solved_at = None
    attempts: list[cognitive_agent.AttemptView] = []
    for row, issue in graded_rows:
        if row.verdict == "accepted":
            last_solved_at, attempts = row.created_at, []
            continue
        attempts.append(cognitive_agent.AttemptView(verdict=row.verdict, ratio=(row.passed / row.total) if row.total else 0.0, issue_key=issue or "unknown"))
    hint_query = select(Hint).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown")
    hints = [h for h in db.scalars(hint_query).all() if last_solved_at is None or h.created_at > last_solved_at]
    last_graded = graded_rows[-1][0] if graded_rows else None
    total = evaluation.get("total") or 0
    return cognitive_agent.CognitiveInput(
        unit_id=unit_id,
        prior_mastery=topic.mastery if topic else cognitive_agent.POLICY["bkt_prior"],
        prior_evidence=topic.evidence_weight if topic else 0.0,
        prior_version=topic.version if topic else 0,
        verdict=evaluation["verdict"], category=diag["category"], issue_key=diag["issue_key"], repeat_count=diag.get("repeat_count", 1),
        ratio=(evaluation.get("passed", 0) / total) if total else 0.0,
        graded=graded,
        same_code_as_previous=bool(last_graded and last_graded.snapshot_id == event["snapshot_id"]),
        difficulty_label=problem.get("difficulty"), source_type=problem.get("source_type", "curriculum"),
        attempts=attempts, hints_on_problem=len(hints),
        max_hint_level_since_last_solve=max((h.level for h in hints), default=0),
        hints_without_progress=sum(1 for h in hints if h.outcome == "no_progress"),
        active_seconds=event.get("active_seconds"), self_confidence=event.get("self_confidence"), self_state=event.get("self_state"),
    )


def _cognitive_fallback(state: dict[str, Any]) -> dict[str, Any]:
    problem = state["context"]["problem"]
    with session_scope() as db:
        topic = db.get(TopicState, (state["event"]["user_id"], problem["unit_id"]))
        prior, evidence, version = (topic.mastery, topic.evidence_weight, topic.version) if topic else (0.2, 0.0, 0)
    output = cognitive_agent.CognitiveOutput(
        unit_id=problem["unit_id"], mastery=cognitive_agent.mastery_estimate(prior, evidence, False, "This estimate could not be updated this time."),
        state_version=version, timestamp=datetime.now(UTC).isoformat(),
    )
    return {"cognitive": output.model_dump()}


@guarded("cognitive_state", "cognitive_state", _cognitive_fallback)
def cognitive_state(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, problem, evaluation, diag = state["event"], state["context"]["problem"], state["evaluation"], state["diagnostic"]
    with session_scope() as db:
        resolved = _resolve_hint_outcomes(db, event, evaluation, diag)
        data = _load_cognitive_input(db, event, problem, evaluation, diag, is_graded(state))
    output = cognitive_agent.run_cognitive(data)
    record.output = {
        "mastery": output.mastery.value, "band": output.mastery.band, "updated": output.mastery.updated, "confidence": output.confidence,
        "confusion": output.confusion, "load": output.cognitive_load, "progress": output.progress, "hints_resolved": resolved,
    }
    return {"cognitive": output.model_dump()}


# ---------------------------------------------------------------- retrieval

def _build_query_vector(state: dict[str, Any], hints_count: int) -> list[float]:
    cog, problem, diag = state["cognitive"], state["context"]["problem"], state["diagnostic"]
    return retrieval_agent.situation_vector(
        mastery=cog["mastery"]["value"], confidence=cog.get("confidence"), confusion=cog.get("confusion"), load=cog.get("cognitive_load"),
        progress=cog.get("progress", "unknown"), difficulty=problem.get("difficulty_score", 0.5),
        attempts=cog.get("graded_attempts_on_problem", 0), hints=hints_count, category=diag["category"],
    )


@guarded("retrieval", "similar_learner_retrieval", lambda state: {"retrieval": retrieval_agent.RetrievalOutput(reliable=False, reason="Retrieval failed, so it was not used this time.").model_dump()})
def retrieval(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, problem, diag = state["event"], state["context"]["problem"], state["diagnostic"]
    with session_scope() as db:
        hints_count = db.scalar(select(func.count()).select_from(Hint).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown")) or 0
        vector = _build_query_vector(state, hints_count)
        output = retrieval_agent.run_retrieval(db, vector, diag["category"], diag["issue_key"], problem["unit_id"], problem.get("difficulty_score", 0.5), event["user_id"])
    record.output = {"reliable": output.reliable, "reason": output.reason, "suggested_level": output.suggested_level, "suggested_strategy": output.suggested_strategy,
                     "effectiveness": output.effectiveness, "support": output.support, "provenance": output.provenance, "similarity": output.mean_similarity, "candidates": output.candidates_considered}
    if not output.reliable:
        record.reason = output.reason
    data = output.model_dump()
    data["query_vector"] = vector
    return {"retrieval": data}


# ---------------------------------------------------------------- DSDA, generation, validation

def _dsda_fallback(state: dict[str, Any]) -> dict[str, Any]:
    event, diag = state["event"], state["diagnostic"]
    explicit = event["trigger"] == "hint_request"
    level = 1 if explicit else 0
    decision = DSDADecision(
        action="give_help" if explicit else "offer_help", level=max(level, 1), level_name=dsda_agent.LEVEL_NAMES[max(level, 1)],
        strategy="conceptual_question", focus_issue=diag["issue_key"], timing="show_now" if explicit else "offer",
        presentation=dsda_agent._presentation(1, None, dsda_agent.POLICY), reason_codes=["POLICY_FAILURE_DEFAULT"],
        reason_student="This is a small starting hint.", policy_version=dsda_agent.POLICY["policy_version"],
    )
    return {"decision": decision.model_dump()}


@guarded("dsda", "adaptive_scaffolding", _dsda_fallback)
def dsda(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, diag, cog = state["event"], state["diagnostic"], state["cognitive"]
    with session_scope() as db:
        hints = db.scalars(
            select(Hint).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown").order_by(Hint.created_at)
        ).all()
    on_issue = [h for h in hints if h.issue_key == diag["issue_key"]]
    data = dsda_agent.DSDAInput(
        trigger=event["trigger"], request_size=event.get("request_size"), category=diag["category"], issue_key=diag["issue_key"],
        repeat_count=diag.get("repeat_count", 1), mastery=cog["mastery"]["value"], mastery_evidence=cog["mastery"]["evidence_weight"],
        confidence=cog.get("confidence"), confusion=cog.get("confusion"), load=cog.get("cognitive_load"), progress=cog.get("progress", "unknown"),
        last_level_on_issue=on_issue[-1].level if on_issue else 0, last_level_any=hints[-1].level if hints else 0,
        last_hint_issue=hints[-1].issue_key if hints else None, hints_on_issue=len(on_issue),
        hints_without_progress_on_issue=sum(1 for h in on_issue if h.outcome == "no_progress"),
        attempts_on_problem=cog.get("graded_attempts_on_problem", 0), retrieval=state.get("retrieval"),
        auto_hints=(state["context"].get("preferences") or {}).get("auto_hints", True),
    )
    decision = dsda_agent.decide(data)
    record.output = {"action": decision.action, "level": decision.level, "strategy": decision.strategy, "timing": decision.timing, "score": decision.score,
                     "components": decision.score_components, "reason_codes": decision.reason_codes, "policy": decision.policy_version, "used_retrieval": decision.used_retrieval}
    return {"decision": decision.model_dump()}


def _safe_built_in(decision: DSDADecision, diag: DiagnosticOutput, reason: str, attempts: int, violations: list[str]) -> dict[str, Any]:
    return hint_agent.as_draft(hint_agent.built_in_hint(decision, diag), "built_in", reason, attempts, violations)


def generate_hint(state: dict[str, Any]) -> dict[str, Any]:
    event, context = state["event"], state["context"]
    decision = DSDADecision(**state["decision"])
    diag = DiagnosticOutput(**state["diagnostic"])
    attempts = state.get("generation_attempts", 0) + 1
    with step(state, "generate_hint", "adaptive_scaffolding", {"level": decision.level, "strategy": decision.strategy, "attempt": attempts}) as record:
        record.retries = attempts - 1
        if not gateway.enabled:
            draft = _safe_built_in(decision, diag, "no_model_configured", attempts, [])
            record.reason = "No model provider is configured, so the built-in hint was used."
        else:
            with session_scope() as db:
                code = db.get(CodeSnapshot, event["snapshot_id"]).code
            try:
                text, meta = hint_agent.generate_ai_hint(decision, diag, context["problem"], code, event.get("question"), state.get("retrieval"), state.get("violations") or [])
                draft = hint_agent.as_draft(text, "ai", None, attempts, state.get("violations") or [])
                record.llm = {"status": "ok", **meta}
            except LLMUnavailable as exc:
                draft = _safe_built_in(decision, diag, "model_unavailable", attempts, [])
                record.status = "fallback"
                record.reason = "The model provider failed, so the built-in hint was used."
                record.llm = {"status": "failed", "reason": str(exc), **gateway.describe()}
        record.output = {"source": draft["source"], "words": len(draft["text"].split())}
    return {"hint": draft, "generation_attempts": attempts}


def validate_hint_node(state: dict[str, Any]) -> dict[str, Any]:
    from .graph import MAX_GENERATION_ATTEMPTS

    event, context = state["event"], state["context"]
    decision = DSDADecision(**state["decision"])
    diag = DiagnosticOutput(**state["diagnostic"])
    draft = dict(state["hint"])
    with step(state, "validate_hint", "adaptive_scaffolding", {"source": draft["source"]}) as record:
        with session_scope() as db:
            solution = db.get(ProblemSolution, event["problem_id"])
            code = db.get(CodeSnapshot, event["snapshot_id"]).code
            evaluation = db.get(Evaluation, state["evaluation"]["id"])
            internal = evaluation.internal_results
        ctx = hint_agent.ValidationContext(
            decision=decision, function_name=context["problem"].get("function_name"), reference_solution=solution.code if solution else None,
            student_code=code, hidden_literals=hint_agent.hidden_literals_from(internal),
        )
        violations = hint_agent.validate_hint(draft["text"], ctx)
        record.output = {"violations": violations, "attempt": state.get("generation_attempts", 1)}
        if not violations:
            return {"hint": draft, "violations": []}
        record.status = "fallback" if draft["source"] == "built_in" or state.get("generation_attempts", 1) >= MAX_GENERATION_ATTEMPTS else "completed"
        record.reason = f"Draft rejected: {', '.join(violations)}."
        if draft["source"] == "ai" and state.get("generation_attempts", 1) < MAX_GENERATION_ATTEMPTS:
            return {"violations": violations}  # loop back: same level, rewritten text
        # Out of retries, or a built-in template collided with this task's solution: use the safest wording.
        safe = _safe_built_in(decision, diag, "validation_fallback", state.get("generation_attempts", 1), violations)
        if hint_agent.validate_hint(safe["text"], ctx):
            lowered = decision.model_copy(update={"level": 1, "presentation": dsda_agent._presentation(1, None, dsda_agent.POLICY)})
            safe["text"] = hint_agent.GENERAL_HINTS[0]
            return {"hint": safe, "violations": [], "decision": lowered.model_dump()}
        return {"hint": safe, "violations": []}


# ---------------------------------------------------------------- reflection

@guarded("reflection", "reflection", lambda state: {"reflection": reflection_agent.ReflectionOutput(action="skip", reason="Reflection failed, so it was skipped.").model_dump()})
def reflection(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, diag, cog, problem = state["event"], state["diagnostic"], state["cognitive"], state["context"]["problem"]
    with session_scope() as db:
        pending = db.scalar(select(func.count()).select_from(Reflection).where(Reflection.user_id == event["user_id"], Reflection.problem_id == event["problem_id"], Reflection.status == "prompted")) or 0
        last = db.scalar(select(Reflection.created_at).where(Reflection.user_id == event["user_id"], Reflection.problem_id == event["problem_id"]).order_by(Reflection.created_at.desc()).limit(1))
        since = None
        if last is not None:
            since = db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.user_id == event["user_id"], Evaluation.problem_id == event["problem_id"], Evaluation.created_at > last, Evaluation.kind == "submit")) or 0
        max_level = db.scalar(select(func.max(Hint.level)).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown")) or 0
    hint = state.get("hint") or {}
    solved = diag["category"] == "accepted"
    output = reflection_agent.decide_reflection(
        category=diag["category"], issue_key=diag["issue_key"], solved=solved, load=cog.get("cognitive_load"), events_since_last_prompt=since, pending=bool(pending),
        graded_attempts=cog.get("graded_attempts_on_problem", 0), max_hint_level=max(max_level, (state.get("decision") or {}).get("level", 0)), hint_text=hint.get("text"),
    )
    output, meta = reflection_agent.personalise_with_llm(output, problem, diag["student_summary"], hint.get("text"))
    record.llm = meta
    record.reason = output.reason
    if output.action != "ask":
        record.status = "skipped" if output.action == "skip" else "deferred"
    record.output = {"action": output.action, "source": output.source}
    return {"reflection": output.model_dump()}


# ---------------------------------------------------------------- planning

def load_planner_views(db, user: User) -> tuple[list[planner_agent.UnitView], list[planner_agent.ProblemView]]:
    states = {s.unit_id: s for s in db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()}
    units = [
        planner_agent.UnitView(
            id=u.id, title=u.title, order=u.order_index, track=u.track, optional=u.optional, prerequisites=u.prerequisites or [],
            mastery=states[u.id].mastery if u.id in states else 0.2, evidence=states[u.id].evidence_weight if u.id in states else 0.0,
            independent=states[u.id].independent_solved if u.id in states else 0, assisted=states[u.id].assisted_solved if u.id in states else 0,
            solved=states[u.id].solved_count if u.id in states else 0,
        )
        for u in db.scalars(select(Unit).order_by(Unit.order_index)).all()
    ]
    solved = set(db.scalars(select(Evaluation.problem_id).where(Evaluation.user_id == user.id, Evaluation.kind == "submit", Evaluation.verdict == "accepted")).all())
    recent = db.execute(
        select(Evaluation.problem_id, func.max(Evaluation.created_at)).where(Evaluation.user_id == user.id, Evaluation.kind == "submit", Evaluation.verdict.notin_(["service_failure", "cancelled"]))
        .group_by(Evaluation.problem_id).order_by(func.max(Evaluation.created_at).desc())
    ).all()
    attempted = {pid: index for index, (pid, _) in enumerate(recent)}
    rows = db.scalars(select(Problem).where(Problem.archived.is_(False), (Problem.owner_id.is_(None)) | (Problem.owner_id == user.id)).order_by(Problem.order_index)).all()
    problems = [
        planner_agent.ProblemView(id=p.id, title=p.title, unit_id=p.unit_id, difficulty=p.difficulty, solved=p.id in solved, attempted=p.id in attempted, recommended_first=p.recommended_first)
        for p in rows if p.owner_id is None or p.id in attempted
    ]
    problems.sort(key=lambda p: attempted.get(p.id, 10**6))
    return units, problems


def _planner_fallback(state: dict[str, Any]) -> dict[str, Any]:
    problem = state["context"]["problem"]
    output = planner_agent.PlanOutput(
        action="continue_current", title=f"Keep going with {problem['title']}", reason="This problem is still your current task.", reason_codes=["PLANNER_FAILURE_DEFAULT"],
        problem_id=problem["id"], problem_title=problem["title"], unit_id=problem["unit_id"],
    )
    return {"plan": output.model_dump()}


@guarded("planner", "learning_planner", _planner_fallback)
def planner(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, diag, cog, problem = state["event"], state["diagnostic"], state["cognitive"], state["context"]["problem"]
    solved_now = diag["category"] == "accepted" and is_graded(state)
    with session_scope() as db:
        user = db.get(User, event["user_id"])
        units, problems = load_planner_views(db, user)
        hints = db.scalars(select(Hint.level).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown")).all()
    max_level = max(hints, default=0)
    for unit in units:
        if unit.id == problem["unit_id"]:
            unit.mastery, unit.evidence = cog["mastery"]["value"], cog["mastery"]["evidence_weight"]
            if solved_now and cog["mastery"]["updated"]:
                unit.solved += 1
                if max_level == 0:
                    unit.independent += 1
                else:
                    unit.assisted += 1
    current = next((p for p in problems if p.id == problem["id"]), None) or planner_agent.ProblemView(id=problem["id"], title=problem["title"], unit_id=problem["unit_id"], difficulty=problem.get("difficulty"))
    if solved_now:
        current.solved = True
    data = planner_agent.PlannerInput(
        units=units, problems=problems, current_problem=current, solved_now=solved_now, unresolved=not solved_now,
        graded_attempts_on_problem=cog.get("graded_attempts_on_problem", 0), max_hint_level_on_problem=max_level,
        goal=state["context"].get("goal"), experience=state["context"].get("experience"),
    )
    output = planner_agent.plan(data)
    record.output = {"action": output.action, "problem_id": output.problem_id, "reason_codes": output.reason_codes}
    return {"plan": output.model_dump()}


# ---------------------------------------------------------------- finalize

def finalize(state: dict[str, Any]) -> dict[str, Any]:
    event, evaluation, context = state["event"], state["evaluation"], state["context"]
    with step(state, "finalize", None) as record:
        with session_scope() as db:
            run = db.get(PipelineRun, event["run_id"])
            if evaluation.get("verdict") in ("service_failure", "cancelled"):
                response = compose.unavailable_response(evaluation, context["problem"], run)
            else:
                response = _persist_learning(db, state, run)
            run.response = response
            run.status = "completed"
            run.policy_version = (state.get("decision") or {}).get("policy_version")
            run.finished_at = datetime.now(UTC)
        record.output = {"verdict": evaluation.get("verdict")}
    log_entry = {"cycle": state.get("cycle", 0), "trigger": event["trigger"], "verdict": evaluation.get("verdict"), "level": (state.get("decision") or {}).get("level")}
    return {"cycle_log": (state.get("cycle_log") or [])[-19:] + [log_entry]}


def _persist_learning(db, state: dict[str, Any], run: PipelineRun) -> dict[str, Any]:
    event, evaluation, context = state["event"], state["evaluation"], state["context"]
    diag, cog, decision, hint, reflection_output, plan_output = (
        state["diagnostic"], state["cognitive"], state["decision"], state.get("hint"), state["reflection"], state["plan"],
    )
    problem = context["problem"]
    db.add(Diagnostic(run_id=run.id, user_id=event["user_id"], problem_id=event["problem_id"], category=diag["category"], issue_key=diag["issue_key"],
                      repeat_count=diag.get("repeat_count", 1), confidence=diag.get("confidence", 0.5), data=diag))

    graded = is_graded(state)
    solved = diag["category"] == "accepted" and graded
    topic = db.get(TopicState, (event["user_id"], problem["unit_id"]), with_for_update=True)
    if topic is None:
        topic = TopicState(user_id=event["user_id"], unit_id=problem["unit_id"], mastery=cognitive_agent.POLICY["bkt_prior"], evidence_weight=0.0, graded_attempts=0, solved_count=0, independent_solved=0, assisted_solved=0, version=0)
        db.add(topic)
    if graded:
        topic.graded_attempts += 1
    if cog["mastery"]["updated"]:
        topic.mastery, topic.evidence_weight, topic.version = cog["mastery"]["value"], cog["mastery"]["evidence_weight"], cog["state_version"]
    if solved and cog["mastery"]["updated"]:
        max_level = db.scalar(select(func.max(Hint.level)).where(Hint.user_id == event["user_id"], Hint.problem_id == event["problem_id"], Hint.delivery == "shown")) or 0
        topic.solved_count += 1
        if max_level == 0:
            topic.independent_solved += 1
        else:
            topic.assisted_solved += 1
    topic.updated_at = datetime.now(UTC)

    db.add(StateSnapshot(
        run_id=run.id, user_id=event["user_id"], unit_id=problem["unit_id"], problem_id=event["problem_id"], version=cog["state_version"], method_version=cog["method_version"],
        mastery=cog["mastery"]["value"], mastery_low=cog["mastery"]["low"], mastery_high=cog["mastery"]["high"], confidence=cog.get("confidence"), confusion=cog.get("confusion"),
        cognitive_load=cog.get("cognitive_load"), progress=cog.get("progress"),
        evidence={"confusion": cog.get("confusion_evidence"), "load": cog.get("load_evidence"), "progress": cog.get("progress_evidence"), "mastery": cog["mastery"]["explanation"]},
    ))

    hint_row = None
    if hint and decision.get("action") == "give_help":
        total = evaluation.get("total") or 0
        hint_row = Hint(
            run_id=run.id, user_id=event["user_id"], problem_id=event["problem_id"], unit_id=problem["unit_id"], snapshot_id=event["snapshot_id"], issue_key=diag["issue_key"],
            category=diag["category"], level=decision["level"], strategy=decision["strategy"], text=hint["text"], source=hint["source"], requested=event["trigger"] == "hint_request",
            delivery="shown", reason_student=decision["reason_student"], reason_codes=decision["reason_codes"], policy_version=decision["policy_version"], score=decision.get("score"),
            validation={"violations_before_final": hint.get("violations"), "attempts": hint.get("attempts"), "built_in_reason": hint.get("built_in_reason"),
                        "baseline_ratio": (evaluation.get("passed", 0) / total) if total else 0.0, "baseline_kind": evaluation.get("kind"),
                        "query_vector": (state.get("retrieval") or {}).get("query_vector")},
            baseline_passed=evaluation.get("passed"),
        )
        db.add(hint_row)

    reflection_row = None
    if reflection_output.get("action") == "ask" and reflection_output.get("prompt"):
        reflection_row = Reflection(run_id=run.id, user_id=event["user_id"], problem_id=event["problem_id"], prompt=reflection_output["prompt"])
        db.add(reflection_row)

    db.add(Recommendation(
        run_id=run.id, user_id=event["user_id"], action=plan_output["action"], problem_id=plan_output.get("problem_id"), unit_id=plan_output.get("unit_id"),
        title=plan_output["title"], reason=plan_output["reason"], reason_codes=plan_output["reason_codes"], alternatives=plan_output.get("alternatives", []),
    ))
    db.add(LearnerEvent(user_id=event["user_id"], problem_id=event["problem_id"], type=event["trigger"], data={"verdict": evaluation.get("verdict"), "run_id": run.id, "level": decision.get("level")}))
    db.flush()
    return compose.tutor_response(state, run, hint_row, reflection_row)
