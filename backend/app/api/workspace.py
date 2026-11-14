"""Run, Submit and Hint are separate endpoints because they mean different things. See tutoring/service.py."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import ratelimit
from ..config import settings
from ..db import get_db
from ..errors import ApiError, forbidden, not_found
from ..grading import parameter_names
from ..models import (
    AgentStep,
    CodeSnapshot,
    Draft,
    Evaluation,
    Hint,
    LearnerEvent,
    PipelineRun,
    Problem,
    Reflection,
    User,
)
from ..schemas import (
    Accepted,
    DraftIn,
    DraftOut,
    EvaluationOut,
    HintFeedbackIn,
    HintIn,
    HintRow,
    ReflectionAnswerIn,
    RunIn,
    RunOut,
    StageOut,
    SubmitIn,
    WorkspaceOut,
)
from ..security import current_user
from ..tutoring import reflection as reflection_agent
from ..tutoring import service
from ..tutoring.dsda import LEVEL_NAMES, STRATEGY_LEVEL_NAMES
from ..tutoring.hints import _normalised_words
from .content import to_detail, visible_problem

router = APIRouter(prefix="/api", tags=["workspace"])


def _evaluation_out(db: Session, evaluation: Evaluation) -> EvaluationOut:
    snapshot = db.get(CodeSnapshot, evaluation.snapshot_id)
    return EvaluationOut(
        id=evaluation.id, kind=evaluation.kind, status=evaluation.status, verdict=evaluation.verdict, passed=evaluation.passed, total=evaluation.total, results=evaluation.public_results or [], message=evaluation.message,
        snapshot_id=evaluation.snapshot_id, code=snapshot.code if snapshot else "", runner_backend=evaluation.runner_backend, runner_secure=evaluation.runner_secure, duration_ms=evaluation.duration_ms,
        created_at=evaluation.created_at, finished_at=evaluation.finished_at,
    )


def _run_out(db: Session, run: PipelineRun) -> RunOut:
    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.sequence)).all()
    evaluation = db.get(Evaluation, run.evaluation_id) if run.evaluation_id else None
    snapshot = db.get(CodeSnapshot, run.snapshot_id)
    return RunOut(
        id=run.id, trigger=run.trigger, status=run.status, problem_id=run.problem_id, snapshot_id=run.snapshot_id, evaluation_id=run.evaluation_id, correlation_id=run.correlation_id, code=snapshot.code if snapshot else "",
        stages=[StageOut(stage=s.stage, agent=s.agent, status=s.status, reason=s.reason, duration_ms=s.duration_ms) for s in steps], response=run.response, evaluation=_evaluation_out(db, evaluation) if evaluation else None,
        created_at=run.created_at, finished_at=run.finished_at,
    )


def _distinct_hints(hints: list[Hint], limit: int = 30) -> list[Hint]:
    """Each different hint once, newest first. Older records can hold exact repeats of the same text."""
    seen: set[str] = set()
    distinct: list[Hint] = []
    for hint in hints:
        key = " ".join(_normalised_words(hint.text))
        if key not in seen:
            seen.add(key)
            distinct.append(hint)
    return distinct[:limit]


def _hint_row(hint: Hint, title: str | None = None) -> HintRow:
    request = hint.learner_request or {}
    return HintRow(id=hint.id, level=hint.level, level_name=STRATEGY_LEVEL_NAMES.get(hint.strategy, LEVEL_NAMES.get(hint.level, "")), strategy=hint.strategy, question=request.get("question"), focus_start=request.get("focus_start"), focus_end=request.get("focus_end"), text=hint.text, why=hint.reason_student, source=hint.source, requested=hint.requested, outcome=hint.outcome, helpful=hint.helpful,
                   problem_id=hint.problem_id, problem_title=title, created_at=hint.created_at)


def _literal(text: str, name: str, number: int) -> Any:
    """Read one value as Python writes it, such as [1, 2] or "abc". Only plain values are allowed, never code."""
    import ast

    try:
        value = ast.literal_eval(text.strip())
    except (ValueError, SyntaxError, MemoryError, RecursionError) as exc:
        raise ApiError(422, "bad_custom_input", f"Case {number}: the value for {name} is not a valid Python value. Write it as you would in code, for example [1, 2], 5 or \"text\".") from exc

    def plain(item: Any) -> Any:
        if isinstance(item, tuple):
            return [plain(x) for x in item]
        if isinstance(item, list):
            return [plain(x) for x in item]
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ApiError(422, "bad_custom_input", f"Case {number}: dictionary keys for {name} must be text here.")
            return {key: plain(val) for key, val in item.items()}
        if item is None or isinstance(item, (bool, int, float, str)):
            return item
        raise ApiError(422, "bad_custom_input", f"Case {number}: {name} can be a number, text, True, False, None, a list or a dictionary.")

    return plain(value)


def _parse_cases(payload: RunIn, problem: Problem) -> dict[str, Any] | None:
    """The test cases shown before running: unchanged examples by id, or values the learner edited or added."""
    if not payload.cases:
        return None
    public_ids = {t.id for t in problem.tests if t.enabled and not t.needs_expected and t.visibility == "public"}
    params = parameter_names(problem.starter_code, problem.function_name)
    cases: list[dict[str, Any]] = []
    for number, case in enumerate(payload.cases, start=1):
        if case.test_id:
            if case.test_id not in public_ids:
                raise ApiError(422, "bad_custom_input", f"Case {number} is not one of this problem's examples.")
            cases.append({"test_id": case.test_id})
        elif case.stdin is not None or problem.mode == "stdio":
            cases.append({"stdin": case.stdin or ""})
        elif case.args is not None:
            if not problem.function_name or len(case.args) != len(params):
                raise ApiError(422, "bad_custom_input", f"Case {number} needs one value for each of: {', '.join(params) or 'the inputs'}.")
            cases.append({"args": [_literal(text, name, number) for text, name in zip(case.args, params, strict=True)]})
        else:
            raise ApiError(422, "bad_custom_input", f"Case {number} is empty.")
    return {"cases": cases}


def _parse_custom(payload: RunIn, problem: Problem) -> dict[str, Any] | None:
    if payload.custom_stdin is not None and payload.custom_stdin != "":
        return {"stdin": payload.custom_stdin}
    if payload.custom_args is not None and payload.custom_args.strip():
        if problem.mode == "stdio" or not problem.function_name:
            return {"stdin": payload.custom_args}
        try:
            args = json.loads(payload.custom_args)
        except ValueError as exc:
            raise ApiError(422, "bad_custom_input", "Your input should be written as a JSON list of arguments, for example [1, 2] or [\"hello\"].") from exc
        if not isinstance(args, list):
            raise ApiError(422, "bad_custom_input", "Your input should be a JSON list of arguments, for example [1, 2].")
        return {"args": args}
    return None


@router.get("/problems/{problem_id}/submissions")
def submissions(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict[str, Any]]:
    """Every graded submission of this problem by this learner, newest first, with the code that was submitted."""
    problem = visible_problem(db, problem_id, user)
    rows = db.scalars(
        select(Evaluation).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id, Evaluation.kind == "submit").order_by(Evaluation.created_at.desc()).limit(200)
    ).all()
    codes = dict(db.execute(select(CodeSnapshot.id, CodeSnapshot.code).where(CodeSnapshot.id.in_([r.snapshot_id for r in rows]))).all()) if rows else {}
    return [{
        "id": row.id, "created_at": row.created_at, "status": row.status, "verdict": row.verdict, "passed": row.passed, "total": row.total,
        "duration_ms": row.duration_ms, "code": codes.get(row.snapshot_id, ""),
        "first_failure": next(({"name": r.get("name"), "category": r.get("category")} for r in (row.public_results or []) if r.get("passed") is False), None),
    } for row in rows]


@router.post("/problems/{problem_id}/run", response_model=Accepted, status_code=202)
def run_code(problem_id: str, payload: RunIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Accepted:
    """Run public examples or the learner's own input. Not graded, and no agents run."""
    ratelimit.check(f"run:{user.id}", settings.rate_run_per_minute)
    problem = visible_problem(db, problem_id, user)
    custom = _parse_cases(payload, problem) or _parse_custom(payload, problem)
    evaluation, created = service.create_run_evaluation(db, user, problem, payload.code, payload.idempotency_key, custom)
    if created:
        db.add(LearnerEvent(user_id=user.id, problem_id=problem.id, type="run", data={"evaluation_id": evaluation.id, "custom": bool(custom)}))
        db.commit()
        service.schedule_evaluation(evaluation)
    return Accepted(id=evaluation.id, created=created)


@router.post("/playground/run", response_model=Accepted, status_code=202)
def run_playground(payload: RunIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Accepted:
    """Run any code from a lesson, in the same sandbox as everything else. Never graded, and no agents run."""
    ratelimit.check(f"run:{user.id}", settings.rate_run_per_minute)
    problem = db.get(Problem, "playground")
    if problem is None:
        raise not_found("The scratch space")
    evaluation, created = service.create_run_evaluation(db, user, problem, payload.code, payload.idempotency_key, None)
    if created:
        service.schedule_evaluation(evaluation)
    return Accepted(id=evaluation.id, created=created)


@router.post("/problems/{problem_id}/submit", response_model=Accepted, status_code=202)
def submit_code(problem_id: str, payload: SubmitIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Accepted:
    """A graded attempt, evaluated on all tests. Starts a learning cycle."""
    ratelimit.check(f"submit:{user.id}", settings.rate_submit_per_minute)
    problem = visible_problem(db, problem_id, user)
    run, created = service.create_learning_run(
        db, user, problem, payload.code, payload.idempotency_key, "submission",
        {"active_seconds": payload.active_seconds, "self_confidence": payload.self_confidence, "self_state": payload.self_state}, payload.active_seconds,
    )
    if created:
        service.schedule_run(run)
    return Accepted(id=run.id, created=created)


@router.post("/problems/{problem_id}/hint", response_model=Accepted, status_code=202)
def request_hint(problem_id: str, payload: HintIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Accepted:
    """A request for help. Uses public examples as evidence. Never counts as a graded attempt."""
    ratelimit.check(f"hint:{user.id}", settings.rate_hint_per_minute)
    problem = visible_problem(db, problem_id, user)
    run, created = service.create_learning_run(
        db, user, problem, payload.code, payload.idempotency_key, "hint_request",
        {"active_seconds": payload.active_seconds, "self_confidence": payload.self_confidence, "self_state": payload.self_state, "request_size": payload.request_size, "question": payload.question, "focus_start": payload.focus_start, "focus_end": payload.focus_end}, payload.active_seconds,
    )
    if created:
        service.schedule_run(run)
    return Accepted(id=run.id, created=created)


def _own_evaluation(db: Session, evaluation_id: str, user: User) -> Evaluation:
    evaluation = db.get(Evaluation, evaluation_id)
    if not evaluation or evaluation.user_id != user.id:
        raise not_found("That result")
    return evaluation


def _own_run(db: Session, run_id: str, user: User) -> PipelineRun:
    run = db.get(PipelineRun, run_id)
    if not run or run.user_id != user.id:
        raise not_found("That result")
    return run


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> EvaluationOut:
    return _evaluation_out(db, _own_evaluation(db, evaluation_id, user))


@router.post("/evaluations/{evaluation_id}/cancel", status_code=202)
def cancel_evaluation(evaluation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    service.cancel_evaluation(db, _own_evaluation(db, evaluation_id, user))
    return {"status": "cancel_requested"}


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> RunOut:
    return _run_out(db, _own_run(db, run_id, user))


@router.post("/runs/{run_id}/cancel", status_code=202)
def cancel_run(run_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    run = _own_run(db, run_id, user)
    if run.evaluation_id:
        service.cancel_evaluation(db, db.get(Evaluation, run.evaluation_id))
    return {"status": "cancel_requested"}


@router.get("/runs/{run_id}/trace")
def run_trace(run_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    """Developer observability. Off in production. Inputs are summaries, so no prompts or hidden tests appear."""
    if settings.is_production:
        raise forbidden("Traces are not available in production.")
    run = _own_run(db, run_id, user)
    steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.sequence)).all()
    return {
        "run_id": run.id, "correlation_id": run.correlation_id, "thread_id": run.thread_id, "status": run.status, "policy_version": run.policy_version, "error": run.error,
        "steps": [{"sequence": s.sequence, "stage": s.stage, "agent": s.agent, "status": s.status, "reason": s.reason, "input": s.input_summary, "output": s.output_summary, "llm": s.llm, "retries": s.retries, "error": s.error, "duration_ms": s.duration_ms} for s in steps],
    }


@router.get("/problems/{problem_id}/workspace", response_model=WorkspaceOut)
def workspace(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> WorkspaceOut:
    problem = visible_problem(db, problem_id, user)
    draft = db.get(Draft, (user.id, problem.id, "python"))
    latest_run = db.scalar(select(PipelineRun).where(PipelineRun.user_id == user.id, PipelineRun.problem_id == problem.id).order_by(PipelineRun.created_at.desc()).limit(1))
    latest_eval = db.scalar(select(Evaluation).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id, Evaluation.kind == "run").order_by(Evaluation.created_at.desc()).limit(1))
    pending = db.scalar(select(Reflection).where(Reflection.user_id == user.id, Reflection.problem_id == problem.id, Reflection.status == "prompted").order_by(Reflection.created_at.desc()).limit(1))
    hints = db.scalars(select(Hint).where(Hint.user_id == user.id, Hint.problem_id == problem.id, Hint.delivery == "shown").order_by(Hint.created_at.desc()).limit(120)).all()
    active = db.scalar(select(func.max(Evaluation.active_seconds)).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id)) or 0
    solved = db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id, Evaluation.kind == "submit", Evaluation.verdict == "accepted")) or 0
    return WorkspaceOut(
        problem=to_detail(db, problem, user), draft=DraftOut(code=draft.code, version=draft.version, updated_at=draft.updated_at) if draft else None, latest_run=_run_out(db, latest_run) if latest_run else None,
        latest_evaluation=_evaluation_out(db, latest_eval) if latest_eval else None, pending_reflection={"id": pending.id, "prompt": pending.prompt} if pending else None, hints=[_hint_row(h) for h in _distinct_hints(list(hints))], active_seconds=active, solved=solved > 0,
    )


@router.put("/problems/{problem_id}/draft", response_model=DraftOut)
def save_draft(problem_id: str, payload: DraftIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> DraftOut:
    problem = visible_problem(db, problem_id, user)
    if len(payload.code) > settings.max_code_chars:
        raise ApiError(413, "code_too_long", f"Your code is longer than the {settings.max_code_chars} character limit.")
    draft = db.get(Draft, (user.id, problem.id, "python"), with_for_update=True)
    now = datetime.now(UTC)
    if draft:
        draft.code, draft.version, draft.updated_at = payload.code, draft.version + 1, now
    else:
        draft = Draft(user_id=user.id, problem_id=problem.id, language="python", code=payload.code, version=1, updated_at=now)
        db.add(draft)
    db.commit()
    return DraftOut(code=draft.code, version=draft.version, updated_at=draft.updated_at)


@router.delete("/problems/{problem_id}/draft", status_code=204)
def delete_draft(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    problem = visible_problem(db, problem_id, user)
    draft = db.get(Draft, (user.id, problem.id, "python"))
    if draft:
        db.delete(draft)
        db.commit()
    return Response(status_code=204)


@router.post("/reflections/{reflection_id}/answer", status_code=200)
def answer_reflection(reflection_id: str, payload: ReflectionAnswerIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    """The answer is its own learner event. It is never graded: the tutor replies to it, and the next cycle can use it."""
    reflection = db.get(Reflection, reflection_id)
    if not reflection or reflection.user_id != user.id:
        raise not_found("That question")
    answer = payload.answer.strip()
    code = db.scalar(select(CodeSnapshot.code).where(CodeSnapshot.user_id == user.id, CodeSnapshot.problem_id == reflection.problem_id).order_by(CodeSnapshot.created_at.desc()).limit(1))
    reply = reflection_agent.respond_to_answer(reflection.kind, reflection.context or {}, answer, code)
    reflection.status, reflection.answer, reflection.answered_at = "answered", answer, datetime.now(UTC)
    reflection.feedback, reflection.quality = reply.feedback, reply.quality
    db.add(LearnerEvent(user_id=user.id, problem_id=reflection.problem_id, type="reflection_answer",
                        data={"reflection_id": reflection.id, "words": len(answer.split()), "quality": reply.quality, "matched": reply.matched}))
    next_step = service.plan_after_reflection(db, user, reflection.problem_id, reply.quality, bool((reflection.context or {}).get("solved")), reflection.run_id)
    db.commit()
    return {"status": "answered", "quality": reply.quality, "feedback": reply.feedback, "matched": reply.matched, "next": next_step}


@router.post("/reflections/{reflection_id}/dismiss", status_code=200)
def dismiss_reflection(reflection_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    reflection = db.get(Reflection, reflection_id)
    if not reflection or reflection.user_id != user.id:
        raise not_found("That question")
    reflection.status = "dismissed"
    db.commit()
    return {"status": "dismissed"}


@router.post("/hints/{hint_id}/feedback", status_code=200)
def hint_feedback(hint_id: str, payload: HintFeedbackIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    hint = db.get(Hint, hint_id)
    if not hint or hint.user_id != user.id:
        raise not_found("That hint")
    hint.helpful = payload.helpful
    db.commit()
    return {"status": "recorded"}
