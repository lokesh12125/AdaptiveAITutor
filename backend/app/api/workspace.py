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
from ..tutoring import service
from ..tutoring.dsda import LEVEL_NAMES
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


def _hint_row(hint: Hint, title: str | None = None) -> HintRow:
    return HintRow(id=hint.id, level=hint.level, level_name=LEVEL_NAMES.get(hint.level, ""), text=hint.text, why=hint.reason_student, source=hint.source, requested=hint.requested, outcome=hint.outcome, helpful=hint.helpful,
                   problem_id=hint.problem_id, problem_title=title, created_at=hint.created_at)


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


@router.post("/problems/{problem_id}/run", response_model=Accepted, status_code=202)
def run_code(problem_id: str, payload: RunIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Accepted:
    """Run public examples or the learner's own input. Not graded, and no agents run."""
    ratelimit.check(f"run:{user.id}", settings.rate_run_per_minute)
    problem = visible_problem(db, problem_id, user)
    custom = _parse_custom(payload, problem)
    evaluation, created = service.create_run_evaluation(db, user, problem, payload.code, payload.idempotency_key, custom)
    if created:
        db.add(LearnerEvent(user_id=user.id, problem_id=problem.id, type="run", data={"evaluation_id": evaluation.id, "custom": bool(custom)}))
        db.commit()
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
        {"active_seconds": payload.active_seconds, "self_confidence": payload.self_confidence, "self_state": payload.self_state, "request_size": payload.request_size, "question": payload.question}, payload.active_seconds,
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
    hints = db.scalars(select(Hint).where(Hint.user_id == user.id, Hint.problem_id == problem.id, Hint.delivery == "shown").order_by(Hint.created_at.desc()).limit(20)).all()
    active = db.scalar(select(func.max(Evaluation.active_seconds)).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id)) or 0
    solved = db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id, Evaluation.kind == "submit", Evaluation.verdict == "accepted")) or 0
    return WorkspaceOut(
        problem=to_detail(db, problem, user), draft=DraftOut(code=draft.code, version=draft.version, updated_at=draft.updated_at) if draft else None, latest_run=_run_out(db, latest_run) if latest_run else None,
        latest_evaluation=_evaluation_out(db, latest_eval) if latest_eval else None, pending_reflection={"id": pending.id, "prompt": pending.prompt} if pending else None, hints=[_hint_row(h) for h in hints], active_seconds=active, solved=solved > 0,
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
def answer_reflection(reflection_id: str, payload: ReflectionAnswerIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    """The answer is its own learner event. It is stored, not graded."""
    reflection = db.get(Reflection, reflection_id)
    if not reflection or reflection.user_id != user.id:
        raise not_found("That question")
    reflection.status, reflection.answer, reflection.answered_at = "answered", payload.answer.strip(), datetime.now(UTC)
    db.add(LearnerEvent(user_id=user.id, problem_id=reflection.problem_id, type="reflection_answer", data={"reflection_id": reflection.id, "words": len(payload.answer.split())}))
    db.commit()
    return {"status": "answered"}


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
