"""Home, progress, assessments, surveys, preferences, and the learner's own data controls."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import analytics
from ..config import settings
from ..db import get_db
from ..errors import ApiError, not_found
from ..models import (
    AssessmentAttempt,
    ClassMember,
    Classroom,
    CodeSnapshot,
    Draft,
    Evaluation,
    Hint,
    InteractionRecord,
    Problem,
    Reflection,
    SurveyResponse,
    TopicState,
    Unit,
    User,
)
from ..runner_client import runner
from ..schemas import (
    AssessmentOut,
    AssessmentSubmitIn,
    ClassJoinIn,
    ClassOut,
    PreferencesIn,
    StatusOut,
    SurveyIn,
    UserOut,
)
from ..security import current_user, verify_password
from ..tutoring import cognitive
from ..tutoring.llm import gateway
from .auth import to_user_out
from .content import LANGUAGES, recommendation_for, statuses
from .workspace import _hint_row

router = APIRouter(prefix="/api", tags=["learner"])
ALLOWED_PREFERENCES = {
    "theme", "editor_font_size", "editor_tab_size", "editor_line_wrap", "editor_line_numbers", "motion", "density", "show_walkthroughs", "auto_hints", "share_anonymous_outcomes",
    "show_estimates", "syntax_feedback", "learning_mode",
}


@router.get("/status", response_model=StatusOut)
def status() -> StatusOut:
    """What this server can do. Contains no secrets. Lets the UI be honest about isolation and AI."""
    health = runner.health()
    isolation = health.get("isolation") or {}
    execution = {
        "available": health.get("status") == "ok", "secure": bool(isolation.get("secure")), "backend": isolation.get("backend"), "label": isolation.get("label", "Unavailable"),
        "note": isolation.get("note"), "properties": isolation.get("properties"), "detail": (health.get("detail") or {}).get("reason"),
    }
    return StatusOut(execution=execution, tutor_model=gateway.describe(), demo_mode=settings.demo_mode, environment=settings.environment, languages=LANGUAGES)


@router.get("/home")
def home(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    plan = recommendation_for(db, user)
    solved, attempted = statuses(db, user.id)
    titles = dict(db.execute(select(Problem.id, Problem.title)).all())
    unit_titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    problem_units = dict(db.execute(select(Problem.id, Problem.unit_id)).all())
    latest = db.execute(
        select(Evaluation.problem_id, func.max(Evaluation.created_at)).where(Evaluation.user_id == user.id, Evaluation.verdict.notin_(["service_failure", "cancelled"])).group_by(Evaluation.problem_id).order_by(func.max(Evaluation.created_at).desc()).limit(40)
    ).all()
    drafts = db.execute(select(Draft.problem_id, Draft.updated_at).where(Draft.user_id == user.id)).all()
    # Archived problems, which include the scratch space behind lesson examples, are not work in progress.
    open_problems = set(db.scalars(select(Problem.id).where(Problem.archived.is_(False))).all())
    moments: dict[str, Any] = {pid: at for pid, at in latest if pid in open_problems}
    for pid, at in drafts:
        if pid in open_problems and (pid not in moments or at > moments[pid]):
            moments[pid] = at
    unfinished = [
        {"problem_id": pid, "title": titles.get(pid, pid), "unit_title": unit_titles.get(problem_units.get(pid, ""), ""), "last_active": at, "attempted": pid in attempted}
        for pid, at in sorted(moments.items(), key=lambda kv: kv[1], reverse=True) if pid not in solved and pid in titles
    ][:6]
    recent = db.scalars(select(Evaluation).where(Evaluation.user_id == user.id, Evaluation.kind == "submit").order_by(Evaluation.created_at.desc()).limit(6)).all()
    states = db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()
    topics = []
    for state in sorted(states, key=lambda s: s.updated_at, reverse=True)[:5]:
        estimate = cognitive.mastery_estimate(state.mastery, state.evidence_weight, False, "")
        topics.append({"unit_id": state.unit_id, "title": unit_titles.get(state.unit_id, state.unit_id), "band": estimate.band, "band_label": analytics.BAND_LABEL[estimate.band], "low": estimate.low, "high": estimate.high})
    return {
        "recommendation": plan.model_dump(), "unfinished": unfinished,
        "recent_activity": [{"problem_id": e.problem_id, "title": titles.get(e.problem_id, e.problem_id), "verdict": e.verdict, "passed": e.passed, "total": e.total, "at": e.created_at} for e in recent],
        "topics": topics, "is_new": not moments and not states, "solved_count": len(solved),
    }


@router.get("/progress")
def progress(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    units = db.scalars(select(Unit).order_by(Unit.order_index)).all()
    states = {s.unit_id: s for s in db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()}
    solved, _ = statuses(db, user.id)
    totals = dict(db.execute(select(Problem.unit_id, func.count()).where(Problem.archived.is_(False), Problem.owner_id.is_(None), Problem.archived.is_(False)).group_by(Problem.unit_id)).all())
    solved_per_unit: dict[str, int] = {}
    if solved:
        for unit_id in db.scalars(select(Problem.unit_id).where(Problem.id.in_(solved))).all():
            solved_per_unit[unit_id] = solved_per_unit.get(unit_id, 0) + 1
    topics = []
    for unit in units:
        state = states.get(unit.id)
        if state:
            estimate = cognitive.mastery_estimate(state.mastery, state.evidence_weight, False, "")
            band, low, high, attempts = estimate.band, estimate.low, estimate.high, state.graded_attempts
        else:
            band, low, high, attempts = "not_enough_evidence", None, None, 0
        topics.append({"unit_id": unit.id, "title": unit.title, "order": unit.order_index, "optional": unit.optional, "band": band, "band_label": analytics.BAND_LABEL[band], "low": low, "high": high, "graded_attempts": attempts,
                       "solved": solved_per_unit.get(unit.id, 0), "total": totals.get(unit.id, 0), "independent": state.independent_solved if state else 0, "assisted": state.assisted_solved if state else 0})
    hints = db.scalars(select(Hint).where(Hint.user_id == user.id, Hint.delivery == "shown").order_by(Hint.created_at.desc()).limit(25)).all()
    titles = dict(db.execute(select(Problem.id, Problem.title)).all())
    reflections = db.scalars(select(Reflection).where(Reflection.user_id == user.id, Reflection.status == "answered").order_by(Reflection.answered_at.desc()).limit(10)).all()
    return {
        "metrics": analytics.learner_metrics(db, [user.id]), "topics": topics, "activity": analytics.activity_by_day(db, [user.id]), "hints": [_hint_row(h, titles.get(h.problem_id)).model_dump() for h in hints],
        "estimates": analytics.latest_estimates(db, user.id), "learning_gain": analytics.learning_gain(db, [user.id]), "satisfaction": analytics.satisfaction(db, [user.id]),
        "reflections": [{"prompt": r.prompt, "answer": r.answer, "at": r.answered_at, "problem_title": titles.get(r.problem_id)} for r in reflections],
    }


def _assessments() -> dict[str, Any]:
    return yaml.safe_load((Path(settings.content_path) / "assessment.yaml").read_text())


@router.get("/assessments/{phase}", response_model=AssessmentOut)
def get_assessment(phase: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> AssessmentOut:
    data = _assessments()
    if phase not in ("pre", "post"):
        raise not_found("That check")
    form = data[phase]
    attempt = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.phase == phase))
    questions = [{"id": q["id"], "prompt": q["prompt"], "code": q.get("code"), "options": q["options"], "unit": q["unit"]} for q in form["questions"]]
    return AssessmentOut(phase=phase, title=form["title"], note=data["note"], questions=questions, completed=attempt is not None, score=attempt.score if attempt else None, max_score=attempt.max_score if attempt else None)


@router.post("/assessments/{phase}", response_model=AssessmentOut)
def submit_assessment(phase: str, payload: AssessmentSubmitIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> AssessmentOut:
    data = _assessments()
    if phase not in ("pre", "post"):
        raise not_found("That check")
    if db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.phase == phase)):
        raise ApiError(409, "already_completed", "You have already completed this check.")
    form = data[phase]
    score = 0
    per_unit: dict[str, list[bool]] = {}
    for question in form["questions"]:
        correct = payload.answers.get(question["id"]) == question["answer"]
        score += 1 if correct else 0
        per_unit.setdefault(question["unit"], []).append(correct)
    db.add(AssessmentAttempt(user_id=user.id, phase=phase, score=score, max_score=len(form["questions"]), answers=payload.answers))
    if phase == "pre":
        # The placement check gives a starting estimate, with little weight, so coding evidence soon dominates.
        for unit_id, results in per_unit.items():
            if not db.get(TopicState, (user.id, unit_id)):
                share = sum(results) / len(results)
                db.add(TopicState(user_id=user.id, unit_id=unit_id, mastery=0.15 + 0.4 * share, evidence_weight=0.5, graded_attempts=0, solved_count=0, independent_solved=0, assisted_solved=0, version=0))
    db.commit()
    return get_assessment(phase, db, user)


@router.post("/survey", status_code=201)
def submit_survey(payload: SurveyIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, str]:
    db.add(SurveyResponse(user_id=user.id, **payload.model_dump()))
    db.commit()
    return {"status": "recorded"}


@router.put("/me/preferences", response_model=UserOut)
def update_preferences(payload: PreferencesIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> UserOut:
    row = db.get(User, user.id)
    updated = dict(row.preferences or {})
    for key, value in payload.preferences.items():
        if key in ALLOWED_PREFERENCES and isinstance(value, (str, int, bool, float, type(None))):
            updated[key] = value
    row.preferences = updated
    db.commit()
    return to_user_out(row)


@router.get("/me/classes", response_model=list[ClassOut])
def my_classes(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[ClassOut]:
    rows = db.scalars(select(Classroom).join(ClassMember, ClassMember.class_id == Classroom.id).where(ClassMember.user_id == user.id)).all()
    return [ClassOut(id=c.id, name=c.name, is_synthetic=c.is_synthetic) for c in rows]


@router.post("/me/classes", response_model=ClassOut, status_code=201)
def join_class(payload: ClassJoinIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ClassOut:
    classroom = db.scalar(select(Classroom).where(Classroom.join_code == payload.join_code.strip().upper(), Classroom.is_synthetic.is_(False)))
    if not classroom:
        raise ApiError(404, "class_not_found", "No class matches that code. Please check it with your teacher.")
    if not db.get(ClassMember, (classroom.id, user.id)):
        db.add(ClassMember(class_id=classroom.id, user_id=user.id))
        db.commit()
    return ClassOut(id=classroom.id, name=classroom.name)


@router.delete("/me/classes/{class_id}", status_code=204)
def leave_class(class_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    db.execute(delete(ClassMember).where(ClassMember.class_id == class_id, ClassMember.user_id == user.id))
    db.commit()
    return Response(status_code=204)


@router.get("/me/profile")
def my_profile(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    """Everything the learner has done, how they have improved, and the estimates the tutor keeps about them."""
    from ..profile import build_profile

    return build_profile(db, user.id)


@router.get("/me/export")
def export_my_data(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    """Everything stored about this learner, for inspection or portability."""
    snapshots = db.scalars(select(CodeSnapshot).where(CodeSnapshot.user_id == user.id)).all()
    evaluations = db.scalars(select(Evaluation).where(Evaluation.user_id == user.id)).all()
    hints = db.scalars(select(Hint).where(Hint.user_id == user.id)).all()
    reflections = db.scalars(select(Reflection).where(Reflection.user_id == user.id)).all()
    states = db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()
    interactions = db.scalars(select(InteractionRecord).where(InteractionRecord.user_id == user.id).order_by(InteractionRecord.created_at)).all()
    return {
        "profile": to_user_out(user).model_dump(),
        "interactions": [{
            "problem_id": r.problem_id, "unit_id": r.unit_id, "trigger": r.trigger, "verdict": r.verdict, "category": r.category, "issue_key": r.issue_key, "tests_passed": r.tests_passed, "tests_total": r.tests_total,
            "code_changed": r.code_changed, "learner_input": r.learner_input, "cognitive": r.cognitive, "decision": r.decision, "active_seconds": r.active_seconds, "policy_version": r.policy_version, "created_at": r.created_at, "reasoning": r.reasoning, "next_action": r.next_action, "resolved": r.resolved,
        } for r in interactions],
        "code_snapshots": [{"problem_id": s.problem_id, "code": s.code, "created_at": s.created_at} for s in snapshots],
        "evaluations": [{"problem_id": e.problem_id, "kind": e.kind, "verdict": e.verdict, "passed": e.passed, "total": e.total, "created_at": e.created_at} for e in evaluations],
        "hints": [{"problem_id": h.problem_id, "level": h.level, "text": h.text, "outcome": h.outcome, "created_at": h.created_at} for h in hints],
        "reflections": [{"problem_id": r.problem_id, "prompt": r.prompt, "answer": r.answer, "status": r.status, "created_at": r.created_at} for r in reflections],
        "topic_estimates": [{"unit_id": s.unit_id, "mastery": s.mastery, "evidence": s.evidence_weight, "updated_at": s.updated_at} for s in states],
    }


class DeleteAccount(PreferencesIn):
    pass


@router.post("/me/delete", status_code=204)
def delete_my_account(body: dict[str, Any], response: Response, password: str = Query(default="", max_length=128), db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    """Removes the account and everything linked to it. Anonymous pooled outcomes have no link back, so they remain."""
    supplied = str(body.get("password") or password)
    if user.password_hash and not verify_password(supplied, user.password_hash):
        raise ApiError(403, "bad_credentials", "Please enter your current password to delete your account.")
    if user.is_synthetic:
        raise ApiError(403, "forbidden", "The shared demo teacher account cannot be deleted.")
    db.delete(db.get(User, user.id))
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie("csmasf_session", path="/")
    return response
