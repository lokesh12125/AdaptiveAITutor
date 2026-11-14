"""Graph nodes. Each one wraps an agent with its persistence boundary and step recording.

Agents are plain functions over typed inputs. Nodes load what those agents need, record what happened,
and fall back safely: one stage failing never loses the learner's code or blocks the rest of the cycle.
All learner-state writes happen together in `finalize`.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
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
    InteractionRecord,
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
from . import questions as question_agent
from . import reflection as reflection_agent
from . import retrieval as retrieval_agent
from .contracts import DiagnosticOutput, DSDADecision, Fact
from .diagnostic import ISSUE_TITLES, PreviousAttempt, compare_with_previous, comparison_facts, run_diagnostic
from .history import InteractionHistory, load_history
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


def history_for(db, state: dict[str, Any]) -> InteractionHistory:
    """Read what has happened so far from the database. Each agent calls this, so nothing it sees is stale."""
    event = state["event"]
    return load_history(db, event["user_id"], event["problem_id"], event["snapshot_id"], (state.get("evaluation") or {}).get("id"))


LADDER_FREE = "answer_question"  # an answer to a question does not use up a step on the ladder


def _reasoning(diag: dict[str, Any], previous: InteractionHistory, hint_row: Hint | None, state: dict[str, Any]) -> dict[str, Any]:
    """The trail behind this hint, so a decision can be checked later. Hidden test contents never reach the evidence used here."""
    evidence = diag.get("evidence") or {}
    known = diag.get("diagnosis") or {}
    return {
        "raw_error": {"type": evidence.get("error_type"), "message": evidence.get("message"), "line": evidence.get("line")} if evidence.get("error_type") else None,
        "error_class": known.get("error_class"), "cause": known.get("cause"), "likely_cause": known.get("likely_cause"), "concept": known.get("concept"), "confidence": known.get("confidence"), "evidence": known.get("evidence"),
        "prior_hints": [{"id": h.id, "strategy": h.strategy, "level": h.level} for h in previous.hints if not hint_row or h.id != hint_row.id][-12:],
        "generated_hint": hint_row.text if hint_row else None,
        "validation": {"passed": hint_row is not None or not state.get("violations"), "rejected": state.get("violations") or [], "attempts": state.get("generation_attempts") or 0, "source": hint_row.source if hint_row else None},
    }


def _note_next_action(db: Any, event: dict[str, Any], evaluation: dict[str, Any], diag: dict[str, Any]) -> None:
    """Complete the previous record: what the learner did after that help, and whether its issue went away."""
    last = db.scalar(select(InteractionRecord).where(InteractionRecord.user_id == event["user_id"], InteractionRecord.problem_id == event["problem_id"]).order_by(InteractionRecord.created_at.desc()).limit(1))
    if last is None or last.next_action is not None:
        return
    code_changed = last.snapshot_id != event["snapshot_id"]
    last.next_action = {"trigger": event["trigger"], "code_changed": code_changed, "verdict": evaluation.get("verdict"), "issue_key": diag["issue_key"], "asked": bool(event.get("question"))}
    last.resolved = diag["category"] == "accepted" or (code_changed and diag["issue_key"] != last.issue_key)


def _attach_observation(output: DiagnosticOutput, code: str, internal: list[dict[str, Any]], problem_id: str) -> None:
    """When the cause is not obvious, run the main loop on a failing example and record what the values did.

    Saying "j stayed 3 on every pass" is evidence a learner can act on, where "trace your code" is not.
    """
    import ast

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return
    loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
    if not loops:
        return
    loop = loops[0]
    span = (loop.lineno, min(loop.end_lineno or loop.lineno, loop.lineno + 14))
    rows = [r for r in internal if r.get("visibility") == "public" and r.get("test_id") and r.get("passed") is False and r.get("origin") != "learner"]
    if not rows:
        return
    from .service import trace_lines

    events = trace_lines(problem_id, code, rows[0]["test_id"], list(range(span[0], span[1] + 1)))
    if not events:
        return
    focus = question_agent.build_focus(code, span, output, auto=True)
    focus.trace_input = str(rows[0].get("input") or "").splitlines()[-1][:120] if rows[0].get("input") else None
    # Count passes on the first line of the body: a while condition is checked once more than the body runs.
    focus.trace, focus.trace_runs = question_agent.summarise_trace(events, focus.trace_input, loop.body[0].lineno if loop.body else None)
    enclosing = next((f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.lineno <= loop.lineno <= (f.end_lineno or f.lineno)), None)
    focus.params = [a.arg for a in enclosing.args.args] if enclosing else []
    if focus.trace:
        output.focus, output.observed = focus, True


def _technique_example(problem_id: str, function_name: str | None) -> dict[str, str] | None:
    """A runnable lesson example of this problem's technique, as long as it is clearly a different task."""
    with session_scope() as db:
        problem = db.get(Problem, problem_id)
        unit = db.get(Unit, problem.unit_id) if problem else None
        reference = db.get(ProblemSolution, problem_id)
        if problem is None or unit is None or not problem.pattern or not unit.guide:
            return None
        wanted = {w for w in problem.pattern.lower().replace("-", " ").split() if len(w) > 3}
        sections = sorted(unit.guide.get("sections") or [], key=lambda s: -len(wanted & set(s.get("title", "").lower().replace("-", " ").split())))
        # Words of this problem's own title, so an example that computes the same thing is never shown as "a different task".
        own = {w for w in re.findall(r"[a-z]+", problem.title.lower()) if len(w) > 3} - {"list", "number", "numbers", "string", "text", "with", "from", "sorted", "values", "value"}
        for section in sections[:1]:
            score = len(wanted & set(section.get("title", "").lower().replace("-", " ").split()))
            if score < min(2, len(wanted)):
                continue
            for example in section.get("examples") or []:
                code = example.get("code") or ""
                if function_name and f"def {function_name}(" in code:
                    continue
                if own & set(re.findall(r"[a-z]+", code.lower())):
                    continue
                if reference and hint_agent.overlap_with_solution(code, reference.code) >= 0.15:
                    continue  # too close to this problem's own solution
                return {"title": example.get("title", "An example"), "code": code.strip(), "note": example.get("note") or "", "technique": problem.pattern}
    return None


def _technique_for(problem_id: str) -> str | None:
    """The technique this problem practises, in the words of the topic's lesson."""
    with session_scope() as db:
        problem = db.get(Problem, problem_id)
        unit = db.get(Unit, problem.unit_id) if problem else None
        if problem is None or unit is None or not problem.pattern:
            return None
        for item in (unit.guide or {}).get("patterns", []):
            if item.get("name") == problem.pattern:
                return f"{item['name']}: {item['how']}"
    return None


def _attach_question(output: DiagnosticOutput, state: dict[str, Any], code: str, internal: list[dict[str, Any]], problem_id: str) -> None:
    """Read what the learner asked and pointed at, and observe what those lines actually do."""
    event = state["event"]
    text = event.get("question")
    question = question_agent.read_question(text, event.get("self_state"))
    span = question_agent.choose_focus(text, event.get("focus_start"), event.get("focus_end"), code)
    auto = False
    if span and question is None:
        question = question_agent.LearnerQuestion(text="", intent="explain_code")
    if question is None:
        return
    output.question = question
    output.technique = _technique_for(problem_id)
    if span is None and question.intent in ("why_fails", "where_wrong", "general", "next_step", "explain_code", "overwhelmed") and output.category not in ("syntax", "accepted"):
        line = output.evidence.line or output.evidence.probe_line
        if line:
            span, auto = (line, line), True
    if span is None:
        return
    focus = question_agent.build_focus(code, span, output, auto)
    output.focus = focus
    if output.category == "syntax":
        return  # nothing has run, so there is nothing to observe
    rows = [r for r in internal if r.get("visibility") == "public" and r.get("test_id") and r.get("origin") != "learner"]
    row = next((r for r in rows if r.get("passed") is False), None) or (rows[0] if rows else None)
    if row is None:
        return
    from .service import trace_lines

    events = trace_lines(problem_id, code, row["test_id"], list(range(focus.start, focus.end + 1)))
    if events is None:
        return
    focus.trace_input = str(row.get("input") or "").splitlines()[-1][:120] if row.get("input") else None
    focus.trace, focus.trace_runs = question_agent.summarise_trace(events, focus.trace_input)
    focus.trace_never_ran = not events and any(line.strip() for line in focus.lines)


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
                    "concepts": problem.concepts, "function_name": problem.function_name, "source_type": problem.source_type, "pattern": problem.pattern,
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
        history = history_for(db, state)
        kind = row.kind
    # Asking again about the same code is not a new occurrence of the issue.
    previous_keys = [issue for issue, snapshot_id in previous if snapshot_id != event["snapshot_id"]]
    same_code_requests = sum(1 for h in history.hints if h.snapshot_id == event["snapshot_id"] and h.strategy != LADDER_FREE)
    last = history.previous_record(event["snapshot_id"])
    previous_attempt = None
    if last is not None:
        previous_attempt = PreviousAttempt(last.snapshot_id, history.previous_code, last.issue_key, last.category, last.evaluation_kind, last.tests_passed, last.tests_total)

    verdict = evaluation["verdict"]
    if verdict == "public_passed":
        passed, total = evaluation["passed"], evaluation["total"]
        output = DiagnosticOutput(
            category="partial", issue_key="logic:public_examples_pass", title="Your code passes the visible examples",
            student_summary=f"All {total} visible examples pass. Submitting checks your code on further tests too.",
            facts=[Fact(kind="public_passed", source="tests", text=f"{passed} of {total} visible examples pass.")],
            concepts=problem.get("concepts", []), confidence=0.8, tests_passed=passed, tests_total=total,
        )
        output.comparison = compare_with_previous(output, code, previous_attempt, kind)
        output.facts.extend(comparison_facts(output, same_code_requests))
        llm_meta = None
    else:
        output, llm_meta = run_diagnostic(verdict, internal, code, problem, previous_keys, previous=previous_attempt, evaluation_kind=kind, same_code_requests=same_code_requests)
    if event["trigger"] == "hint_request":
        _attach_question(output, state, code, internal, event["problem_id"])
    if output.question is None and output.issue_key == "logic:general" and output.category in ("wrong_answer", "partial"):
        _attach_observation(output, code, internal, event["problem_id"])
    if output.category in ("wrong_answer", "partial"):
        output.technique_example = _technique_example(event["problem_id"], problem.get("function_name"))
    record.llm = llm_meta
    comparison = output.comparison
    record.output = {
        "category": output.category, "issue_key": output.issue_key, "confidence": output.confidence, "repeat_count": output.repeat_count, "facts": len(output.facts), "same_code_requests": same_code_requests,
        "has_previous": comparison.has_previous, "same_issue": comparison.same_issue, "moved_further": comparison.moved_further, "tests_delta": comparison.tests_delta, "changed_lines": comparison.changed_lines[:10],
        "question_intent": output.question.intent if output.question else None, "focus": [output.focus.start, output.focus.end] if output.focus else None, "traced": bool(output.focus and (output.focus.trace or output.focus.trace_never_ran)),
        # The cause is held back from the learner's first view, but the trace (development only) records it for auditing.
        "cause": output.diagnosis.cause if output.diagnosis else None, "concept": output.diagnosis.concept if output.diagnosis else None,
        "cause_confidence": output.diagnosis.confidence if output.diagnosis else None,
    }
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
        unit_id=hint.unit_id, category=retrieval_agent.category_group(hint.category), issue_key=dsda_agent.base_issue(hint.issue_key),
        difficulty=problem.difficulty_score, level=hint.level, strategy=hint.strategy, outcome=hint.outcome, vector=vector,
    )
    db.add(case)
    db.flush()
    try:
        retrieval_agent.store.upsert_case(case)
    except Exception as exc:  # noqa: BLE001 - the relational record is kept; the vector can be reindexed
        log.warning("could not index case: %s", type(exc).__name__)


def _load_cognitive_input(db, event: dict[str, Any], problem: dict[str, Any], evaluation: dict[str, Any], diag: dict[str, Any], graded: bool, history: InteractionHistory | None = None) -> cognitive_agent.CognitiveInput:
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
    comparison = diag.get("comparison") or {}
    same_measure = history.previous_record_of_kind(event["snapshot_id"], evaluation.get("kind")) if history else None
    prior_rating = db.scalar(
        select(StateSnapshot.confidence).where(StateSnapshot.user_id == event["user_id"], StateSnapshot.problem_id == event["problem_id"], StateSnapshot.confidence.is_not(None))
        .order_by(StateSnapshot.created_at.desc()).limit(1)
    )
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
        active_seconds=event.get("active_seconds"), self_confidence=event.get("self_confidence"), self_state=event.get("self_state") or ("stuck" if (diag.get("question") or {}).get("stuck") else None),
        same_code_requests=sum(1 for h in hints if h.snapshot_id == event["snapshot_id"] and h.strategy != LADDER_FREE), hints_marked_unhelpful=sum(1 for h in hints if h.helpful is False),
        reflection_unsure=bool(history and history.reflection_unsure_since_last_cycle),
        prior_self_confidence=prior_rating, code_changed=bool(comparison.get("has_previous")), moved_further=bool(comparison.get("moved_further")),
        previous_ratio_same_measure=(same_measure.tests_passed / same_measure.tests_total) if same_measure and same_measure.tests_total else None,
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
        data = _load_cognitive_input(db, event, problem, evaluation, diag, is_graded(state), history_for(db, state))
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
        history = history_for(db, state)
        vector = _build_query_vector(state, len(history.hints))
        tried = [h.strategy for h in history.hints_on_issue(diag["issue_key"])]
        output = retrieval_agent.run_retrieval(db, vector, diag["category"], dsda_agent.base_issue(diag["issue_key"]), problem["unit_id"], problem.get("difficulty_score", 0.5), event["user_id"], exclude_strategies=tried)
    record.output = {"reliable": output.reliable, "reason": output.reason, "suggested_level": output.suggested_level, "suggested_strategy": output.suggested_strategy, "excluded": output.excluded_strategies,
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
    decision = DSDADecision(
        action="give_help" if explicit else "offer_help", selected_level=1, level_name=dsda_agent.LEVEL_NAMES[1],
        strategy="conceptual_question", focus_issue=diag["issue_key"], timing="show_now" if explicit else "offer", theme=dsda_agent.theme_for(diag["category"], diag["issue_key"]),
        presentation=dsda_agent._presentation(1, None, dsda_agent.POLICY), reason_codes=["POLICY_FAILURE_DEFAULT"],
        reason_student="This is a small starting hint.", policy_version=dsda_agent.POLICY["policy_version"],
    )
    return {"decision": decision.model_dump()}


@guarded("dsda", "adaptive_scaffolding", _dsda_fallback)
def dsda(state: dict[str, Any], record: StepRecord) -> dict[str, Any]:
    event, diag, cog = state["event"], state["diagnostic"], state["cognitive"]
    with session_scope() as db:
        history = history_for(db, state)
    hints = [h for h in history.hints if h.strategy != LADDER_FREE]
    on_issue = [h for h in history.hints_on_issue(diag["issue_key"]) if h.strategy != LADDER_FREE]
    last_on_issue = on_issue[-1] if on_issue else None
    comparison = diag.get("comparison") or {}
    evidence = diag.get("evidence") or {}
    data = dsda_agent.DSDAInput(
        trigger=event["trigger"], request_size=event.get("request_size"), category=diag["category"], issue_key=diag["issue_key"],
        repeat_count=diag.get("repeat_count", 1), mastery=cog["mastery"]["value"], mastery_evidence=cog["mastery"]["evidence_weight"],
        confidence=cog.get("confidence"), confusion=cog.get("confusion"), load=cog.get("cognitive_load"), progress=cog.get("progress", "unknown"),
        last_level_on_issue=last_on_issue.level if last_on_issue else 0, last_level_any=hints[-1].level if hints else 0,
        last_hint_issue=hints[-1].issue_key if hints else None, hints_on_issue=len(on_issue),
        hints_without_progress_on_issue=sum(1 for h in on_issue if h.outcome == "no_progress"),
        attempts_on_problem=cog.get("graded_attempts_on_problem", 0), retrieval=state.get("retrieval"),
        # Practice mode means fewer hints nobody asked for. A request for help is always answered.
        auto_hints=(state["context"].get("preferences") or {}).get("auto_hints", True) and (state["context"].get("preferences") or {}).get("learning_mode") != "practice",
        used_strategies=[h.strategy for h in on_issue], same_code_hints=sum(1 for h in on_issue if h.snapshot_id == event["snapshot_id"]), has_question=bool(diag.get("question")),
        code_changed_since_last_hint=bool(last_on_issue and last_on_issue.snapshot_id != event["snapshot_id"]), moved_further=bool(comparison.get("moved_further")),
        last_hint_helpful=last_on_issue.helpful if last_on_issue else None, last_hint_outcome=last_on_issue.outcome if last_on_issue else None,
        seconds_since_last_hint=history.seconds_since_last_hint(), seconds_since_last_action=history.seconds_since_last_action(),
        has_failing_example=bool(evidence.get("failing_example")),
    )
    decision = dsda_agent.decide(data)
    record.output = {"action": decision.action, "selected_level": decision.selected_level, "strategy": decision.strategy, "timing": decision.timing, "support_need_score": decision.support_need_score,
                     "components": decision.score_components, "reason_codes": decision.reason_codes, "policy": decision.policy_version, "used_retrieval": decision.used_retrieval,
                     "hints_on_issue": data.hints_on_issue, "same_code_hints": data.same_code_hints, "used_strategies": data.used_strategies}
    return {"decision": decision.model_dump()}


def _safe_built_in(decision: DSDADecision, diag: DiagnosticOutput, reason: str, attempts: int, violations: list[str]) -> dict[str, Any]:
    return hint_agent.as_draft(hint_agent.built_in_hint(decision, diag), "built_in", reason, attempts, violations)


def generate_hint(state: dict[str, Any]) -> dict[str, Any]:
    event, context = state["event"], state["context"]
    decision = DSDADecision(**state["decision"])
    diag = DiagnosticOutput(**state["diagnostic"])
    attempts = state.get("generation_attempts", 0) + 1
    with step(state, "generate_hint", "adaptive_scaffolding", {"selected_level": decision.selected_level, "strategy": decision.strategy, "attempt": attempts}) as record:
        record.retries = attempts - 1
        if not gateway.enabled:
            draft = _safe_built_in(decision, diag, "no_model_configured", attempts, [])
            record.reason = "No model provider is configured, so the built-in hint was used."
        else:
            with session_scope() as db:
                code = db.get(CodeSnapshot, event["snapshot_id"]).code
                prior = [h.text for h in history_for(db, state).hints]
            try:
                text, meta = hint_agent.generate_ai_hint(decision, diag, context["problem"], code, event.get("question"), state.get("retrieval"), state.get("violations") or [], prior)
                draft = hint_agent.as_draft(text, "ai", None, attempts, state.get("violations") or [])
                record.llm = {"status": "ok", **meta}
            except LLMUnavailable as exc:
                draft = _safe_built_in(decision, diag, "model_unavailable", attempts, [])
                record.status = "fallback"
                record.reason = "The model provider failed, so the built-in hint was used."
                record.llm = {"status": "failed", "reason": str(exc), **gateway.describe()}
        record.output = {"source": draft["source"], "words": len(draft["text"].split())}
    return {"hint": draft, "generation_attempts": attempts}


def _next_new_hint(decision: DSDADecision, diag: DiagnosticOutput, ctx: hint_agent.ValidationContext, used: list[str]) -> tuple[DSDADecision, str] | None:
    """The drafted hint cannot be shown. Find the next step on the ladder whose built-in text can be."""
    policy = dsda_agent.POLICY
    tried = set(used) | {decision.strategy}
    for step_option in dsda_agent.ladder_for(diag.category, diag.issue_key, diag.evidence.failing_example is not None, policy):
        # Only the same or the next level: a fallback must not hand out much more help, or drop back to much less.
        if step_option.strategy in tried or not decision.selected_level <= step_option.level <= decision.selected_level + 1:
            continue
        load = "high" if decision.presentation.one_action_at_a_time else None
        candidate = decision.model_copy(update={
            "strategy": step_option.strategy, "selected_level": step_option.level, "level_name": dsda_agent.STRATEGY_LEVEL_NAMES.get(step_option.strategy, dsda_agent.LEVEL_NAMES[step_option.level]),
            "presentation": dsda_agent._presentation(step_option.level, load, policy), "constraints": decision.constraints.model_copy(update={"allow_analogous_example": step_option.level == 4}),
        })
        text = hint_agent.built_in_hint(candidate, diag)
        if not hint_agent.validate_hint(text, replace(ctx, decision=candidate)):
            return candidate, text
    return None


def validate_hint_node(state: dict[str, Any]) -> dict[str, Any]:
    from .graph import MAX_GENERATION_ATTEMPTS

    event, context = state["event"], state["context"]
    decision = DSDADecision(**state["decision"])
    diag = DiagnosticOutput(**state["diagnostic"])
    draft = dict(state["hint"])
    attempts = state.get("generation_attempts", 1)
    with step(state, "validate_hint", "adaptive_scaffolding", {"source": draft["source"]}) as record:
        with session_scope() as db:
            solution = db.get(ProblemSolution, event["problem_id"])
            code = db.get(CodeSnapshot, event["snapshot_id"]).code
            evaluation = db.get(Evaluation, state["evaluation"]["id"])
            internal = evaluation.internal_results
            history = history_for(db, state)
        ctx = hint_agent.ValidationContext(
            decision=decision, function_name=context["problem"].get("function_name"), reference_solution=solution.code if solution else None,
            student_code=code, hidden_literals=hint_agent.hidden_literals_from(internal), prior_hints=[h.text for h in history.hints],
            repeat_threshold=dsda_agent.POLICY["repeat_similarity_threshold"], diagnostic=diag, require_on_topic=draft["source"] == "ai",
        )
        violations = hint_agent.validate_hint(draft["text"], ctx)
        similarity = max((hint_agent.hint_similarity(draft["text"], h.text) for h in history.hints), default=0.0)
        record.output = {"violations": violations, "attempt": attempts, "max_similarity_to_prior": round(similarity, 3), "prior_hints_checked": len(history.hints)}
        if not violations:
            return {"hint": draft, "violations": []}
        log.warning("hint rejected (source=%s, attempt=%s, correlation=%s): %s", draft["source"], attempts, event.get("correlation_id"), ", ".join(violations))
        record.status = "fallback" if draft["source"] == "built_in" or attempts >= MAX_GENERATION_ATTEMPTS else "completed"
        record.reason = f"Draft rejected: {', '.join(violations)}."
        if draft["source"] == "ai" and attempts < MAX_GENERATION_ATTEMPTS:
            return {"violations": violations}  # loop back: same level and strategy, rewritten text
        # Out of retries, or a built-in template collided with something: use a deterministic hint that passes.
        safe = _safe_built_in(decision, diag, "validation_fallback", attempts, violations)
        built_in_ctx = replace(ctx, require_on_topic=False)
        if not hint_agent.validate_hint(safe["text"], built_in_ctx):
            return {"hint": safe, "violations": []}
        if decision.strategy == LADDER_FREE:
            # Another angle on the same question is better than moving on from it.
            for text in question_agent.answer_candidates(diag):
                fitted = hint_agent.fit_to_presentation(text, decision)
                if not hint_agent.validate_hint(fitted, built_in_ctx):
                    safe["text"] = fitted
                    return {"hint": safe, "violations": []}
        replacement = _next_new_hint(decision, diag, built_in_ctx, [h.strategy for h in history.hints_on_issue(diag.issue_key) if h.strategy != LADDER_FREE])
        if replacement is not None:
            candidate, text = replacement
            safe["text"] = text
            return {"hint": safe, "violations": [], "decision": candidate.model_dump()}
        # Nothing new can be said without repeating or leaking, so wait rather than show a bad hint.
        record.reason = f"Draft rejected: {', '.join(violations)}. No other hint could pass, so the tutor is waiting for the learner."
        codes = [*decision.reason_codes, "LADDER_EXHAUSTED"]
        waiting = decision.model_copy(update={
            "action": "wait", "selected_level": 0, "level_name": dsda_agent.LEVEL_NAMES[0], "strategy": "await_code_change", "timing": "wait_for_learner",
            "presentation": dsda_agent._presentation(0, None, dsda_agent.POLICY), "reason_codes": codes, "reason_student": dsda_agent.REASONS["LADDER_EXHAUSTED"],
        })
        return {"hint": None, "violations": [], "decision": waiting.model_dump()}


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
        history = history_for(db, state)
    hint = state.get("hint") or {}
    solved = diag["category"] == "accepted"
    output = reflection_agent.decide_reflection(
        category=diag["category"], issue_key=diag["issue_key"], solved=solved, load=cog.get("cognitive_load"), events_since_last_prompt=since, pending=bool(pending),
        graded_attempts=cog.get("graded_attempts_on_problem", 0), max_hint_level=max(max_level, (state.get("decision") or {}).get("selected_level", 0)), hint_text=hint.get("text"),
        previous_prompts=history.reflection_prompts, context=_reflection_context(diag, problem),
    )
    output, meta = reflection_agent.personalise_with_llm(output, problem, diag["student_summary"], hint.get("text"))
    record.llm = meta
    record.reason = output.reason
    if output.action != "ask":
        record.status = "skipped" if output.action == "skip" else "deferred"
    record.output = {"action": output.action, "source": output.source}
    return {"reflection": output.model_dump()}


def _reflection_context(diag: dict[str, Any], problem: dict[str, Any]) -> dict[str, Any]:
    """What the question and the later reply may name: the learner's own example, loop and line, and the technique."""
    evidence = diag.get("evidence") or {}
    example = evidence.get("failing_example") or {}
    known = diag.get("diagnosis") or {}
    return {k: v for k, v in {
        "issue_key": diag.get("issue_key"), "category": diag.get("category"), "concept": known.get("concept"), "pattern": problem.get("pattern"),
        "input": example.get("input"), "got": example.get("got"), "expected": example.get("expected"),
        "loop_source": evidence.get("loop_source"), "loop_variable": evidence.get("loop_variable"), "result_name": evidence.get("result_name"),
        "line": evidence.get("line") or (diag.get("affected_lines") or [None])[0],
    }.items() if v is not None}


# ---------------------------------------------------------------- planning

def _fluent_solves(db, user: User) -> set[str]:
    """Problems solved on the first graded submission, with no hint shown before it. The planner counts one of these
    as a technique practised, the same rule it applies right after such a solve."""
    first_hint = dict(db.execute(select(Hint.problem_id, func.min(Hint.created_at)).where(Hint.user_id == user.id, Hint.delivery == "shown").group_by(Hint.problem_id)).all())
    graded = db.execute(
        select(Evaluation.problem_id, Evaluation.verdict, Evaluation.created_at)
        .where(Evaluation.user_id == user.id, Evaluation.kind == "submit", Evaluation.verdict.notin_(["service_failure", "cancelled"]))
        .order_by(Evaluation.created_at)
    ).all()
    seen: set[str] = set()
    fluent: set[str] = set()
    for problem_id, verdict, at in graded:
        if problem_id in seen:
            continue
        seen.add(problem_id)
        if verdict == "accepted" and (problem_id not in first_hint or first_hint[problem_id] > at):
            fluent.add(problem_id)
    return fluent


def load_planner_views(db, user: User) -> tuple[list[planner_agent.UnitView], list[planner_agent.ProblemView]]:
    states = {s.unit_id: s for s in db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()}
    units = [
        planner_agent.UnitView(
            id=u.id, title=u.title, order=u.order_index, track=u.track, optional=u.optional, prerequisites=u.prerequisites or [],
            mastery=states[u.id].mastery if u.id in states else 0.2, evidence=states[u.id].evidence_weight if u.id in states else 0.0,
            independent=states[u.id].independent_solved if u.id in states else 0, assisted=states[u.id].assisted_solved if u.id in states else 0,
            solved=states[u.id].solved_count if u.id in states else 0,
            patterns=[p.get("name") for p in (u.guide or {}).get("patterns", []) if p.get("name")],
        )
        for u in db.scalars(select(Unit).order_by(Unit.order_index)).all()
    ]
    solved = set(db.scalars(select(Evaluation.problem_id).where(Evaluation.user_id == user.id, Evaluation.kind == "submit", Evaluation.verdict == "accepted")).all())
    recent = db.execute(
        select(Evaluation.problem_id, func.max(Evaluation.created_at)).where(Evaluation.user_id == user.id, Evaluation.kind == "submit", Evaluation.verdict.notin_(["service_failure", "cancelled"]))
        .group_by(Evaluation.problem_id).order_by(func.max(Evaluation.created_at).desc())
    ).all()
    attempted = {pid: index for index, (pid, _) in enumerate(recent)}
    fluent = _fluent_solves(db, user)
    rows = db.scalars(select(Problem).where(Problem.archived.is_(False), (Problem.owner_id.is_(None)) | (Problem.owner_id == user.id)).order_by(Problem.order_index)).all()
    problems = [
        planner_agent.ProblemView(id=p.id, title=p.title, unit_id=p.unit_id, difficulty=p.difficulty, solved=p.id in solved, attempted=p.id in attempted, recommended_first=p.recommended_first, pattern=p.pattern,
                                   fluent=p.id in fluent)
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
    current = next((p for p in problems if p.id == problem["id"]), None) or planner_agent.ProblemView(id=problem["id"], title=problem["title"], unit_id=problem["unit_id"], difficulty=problem.get("difficulty"), pattern=problem.get("pattern"))
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
    log_entry = {"cycle": state.get("cycle", 0), "trigger": event["trigger"], "verdict": evaluation.get("verdict"), "level": (state.get("decision") or {}).get("selected_level")}
    return {"cycle_log": (state.get("cycle_log") or [])[-19:] + [log_entry]}


def _learner_request(diag: dict[str, Any]) -> dict[str, Any] | None:
    question, focus = diag.get("question"), diag.get("focus")
    if not question and not focus:
        return None
    return {"question": (question or {}).get("text") or None, "intent": (question or {}).get("intent"), "focus_start": (focus or {}).get("start"), "focus_end": (focus or {}).get("end"), "auto_focus": (focus or {}).get("auto", False)}


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
            category=diag["category"], level=decision["selected_level"], strategy=decision["strategy"], text=hint["text"], source=hint["source"], requested=event["trigger"] == "hint_request",
            delivery="shown", reason_student=decision["reason_student"], reason_codes=decision["reason_codes"], policy_version=decision["policy_version"], score=decision.get("support_need_score"),
            validation={"violations_before_final": hint.get("violations"), "attempts": hint.get("attempts"), "built_in_reason": hint.get("built_in_reason"),
                        "baseline_ratio": (evaluation.get("passed", 0) / total) if total else 0.0, "baseline_kind": evaluation.get("kind"),
                        "query_vector": (state.get("retrieval") or {}).get("query_vector")},
            baseline_passed=evaluation.get("passed"),
            learner_request=_learner_request(diag),
        )
        db.add(hint_row)

    reflection_row = None
    if reflection_output.get("action") == "ask" and reflection_output.get("prompt"):
        reflection_row = Reflection(run_id=run.id, user_id=event["user_id"], problem_id=event["problem_id"], prompt=reflection_output["prompt"],
                                    kind=reflection_output.get("kind"), context=reflection_output.get("context") or {})
        db.add(reflection_row)

    db.add(Recommendation(
        run_id=run.id, user_id=event["user_id"], action=plan_output["action"], problem_id=plan_output.get("problem_id"), unit_id=plan_output.get("unit_id"),
        title=plan_output["title"], reason=plan_output["reason"], reason_codes=plan_output["reason_codes"], alternatives=plan_output.get("alternatives", []),
    ))
    db.add(LearnerEvent(user_id=event["user_id"], problem_id=event["problem_id"], type=event["trigger"], data={"verdict": evaluation.get("verdict"), "run_id": run.id, "level": decision.get("selected_level")}))
    db.flush()

    # The next cycle reads this back. Read the earlier count first, so this hint does not count itself.
    previous = load_history(db, event["user_id"], event["problem_id"], event["snapshot_id"], evaluation.get("id"))
    on_issue_rows = [h for h in previous.hints_on_issue(diag["issue_key"]) if not hint_row or h.id != hint_row.id]
    earlier_on_issue = sum(1 for h in on_issue_rows if h.strategy != LADDER_FREE)
    distinct_on_issue = len({" ".join(hint_agent._normalised_words(h.text)) for h in on_issue_rows})
    comparison = diag.get("comparison") or {}
    last_record = previous.records[-1] if previous.records else None
    retrieval_row = dict(state.get("retrieval") or {}) or None
    _note_next_action(db, event, evaluation, diag)
    db.add(InteractionRecord(
        run_id=run.id, user_id=event["user_id"], problem_id=event["problem_id"], unit_id=problem["unit_id"], snapshot_id=event["snapshot_id"], evaluation_id=evaluation.get("id"), evaluation_kind=evaluation.get("kind"),
        trigger=event["trigger"], verdict=evaluation.get("verdict"), category=diag["category"], issue_key=diag["issue_key"], tests_passed=evaluation.get("passed") or 0, tests_total=evaluation.get("total") or 0,
        code_changed=bool(comparison.get("has_previous")) and (last_record is None or last_record.snapshot_id != event["snapshot_id"]),
        learner_input={k: event.get(k) for k in ("request_size", "question", "focus_start", "focus_end", "self_confidence", "self_state")},
        diagnostic={k: diag.get(k) for k in ("title", "student_summary", "facts", "inferences", "affected_lines", "confidence", "uncertain", "repeat_count", "evidence", "comparison", "question", "focus", "source", "diagnosis")},
        cognitive=cog, retrieval=retrieval_row, decision=decision, hint_id=hint_row.id if hint_row else None, active_seconds=event.get("active_seconds"), policy_version=decision.get("policy_version"),
        reasoning=_reasoning(diag, previous, hint_row, state),
    ))
    db.flush()
    same_code_cycles = sum(1 for r in previous.records if r.snapshot_id == event["snapshot_id"])
    return compose.tutor_response(state, run, hint_row, reflection_row, earlier_on_issue, same_code_cycles, distinct_on_issue)
