"""Teacher views. Access is checked on the server for every request: teachers see only their own classes."""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import analytics
from ..db import get_db
from ..errors import forbidden, not_found
from ..models import ClassMember, Classroom, Evaluation, Hint, Problem, TopicState, Unit, User
from ..schemas import ClassCreateIn, ClassOut
from ..security import require_teacher, teacher_can_view_student
from ..tutoring import cognitive
from .workspace import _hint_row

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _own_class(db: Session, class_id: str, teacher: User) -> Classroom:
    classroom = db.get(Classroom, class_id)
    if not classroom or classroom.teacher_id != teacher.id:
        raise not_found("That class")
    return classroom


@router.get("/classes", response_model=list[ClassOut])
def list_classes(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)) -> list[ClassOut]:
    rows = db.scalars(select(Classroom).where(Classroom.teacher_id == teacher.id).order_by(Classroom.created_at)).all()
    counts = dict(db.execute(select(ClassMember.class_id, func.count()).group_by(ClassMember.class_id)).all())
    return [ClassOut(id=c.id, name=c.name, join_code=c.join_code, is_synthetic=c.is_synthetic, members=counts.get(c.id, 0)) for c in rows]


@router.post("/classes", response_model=ClassOut, status_code=201)
def create_class(payload: ClassCreateIn, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)) -> ClassOut:
    classroom = Classroom(name=payload.name.strip(), teacher_id=teacher.id, join_code=secrets.token_hex(4).upper())
    db.add(classroom)
    db.commit()
    return ClassOut(id=classroom.id, name=classroom.name, join_code=classroom.join_code, is_synthetic=False, members=0)


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: str, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)) -> Response:
    classroom = _own_class(db, class_id, teacher)
    if classroom.is_synthetic:
        raise forbidden("The demo class cannot be deleted.")
    db.delete(classroom)
    db.commit()
    return Response(status_code=204)


@router.get("/classes/{class_id}/overview")
def overview(class_id: str, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)) -> dict[str, Any]:
    classroom = _own_class(db, class_id, teacher)
    members = analytics.class_member_ids(db, class_id)
    users = db.scalars(select(User).where(User.id.in_(members)).order_by(User.name)).all() if members else []
    learners = []
    for user in users:
        metrics = analytics.learner_metrics(db, [user.id])
        last = db.scalar(select(func.max(Evaluation.created_at)).where(Evaluation.user_id == user.id))
        flags = analytics.learner_flags(db, user.id)
        learners.append({"id": user.id, "name": user.name, "solved": metrics["solved"], "started": metrics["started"], "completion_rate": metrics["completion_rate"], "hints_per_solved": metrics["hints_per_solved"], "last_active": last, "flags": flags})
    return {
        "class": {"id": classroom.id, "name": classroom.name, "join_code": classroom.join_code, "is_synthetic": classroom.is_synthetic, "members": len(members)},
        "metrics": analytics.learner_metrics(db, members), "topics": analytics.topic_difficulties(db, members), "common_errors": analytics.common_errors(db, members), "assistance": analytics.assistance(db, members),
        "activity": analytics.activity_by_day(db, members), "learning_gain": analytics.learning_gain(db, members), "satisfaction": analytics.satisfaction(db, members), "learners": learners,
        "needs_support": [{"id": row["id"], "name": row["name"], "flags": row["flags"]} for row in learners if row["flags"]],
        "definitions": {
            "completion_rate": "Problems solved ÷ problems with at least one graded attempt.", "hints_per_solved": "Hints shown on solved problems ÷ problems solved. Hints on unsolved problems are not counted.",
            "time_to_complete": "Median active seconds at the first accepted submission. Solves with no recorded time are left out.", "hint_progress": "Hints followed by progress or a solve ÷ hints with a known outcome. Progress after a hint does not prove the hint caused it.",
            "first_try_rate": "Problems accepted on the first graded attempt ÷ problems attempted.",
        },
    }


@router.get("/classes/{class_id}/students/{student_id}")
def student_detail(class_id: str, student_id: str, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)) -> dict[str, Any]:
    _own_class(db, class_id, teacher)
    if not db.get(ClassMember, (class_id, student_id)) or not teacher_can_view_student(db, teacher, student_id):
        raise not_found("That learner")
    student = db.get(User, student_id)
    titles = dict(db.execute(select(Problem.id, Problem.title)).all())
    unit_titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    states = db.scalars(select(TopicState).where(TopicState.user_id == student_id)).all()
    topics = []
    for state in states:
        estimate = cognitive.mastery_estimate(state.mastery, state.evidence_weight, False, "")
        topics.append({"unit_id": state.unit_id, "title": unit_titles.get(state.unit_id, state.unit_id), "band": estimate.band, "band_label": analytics.BAND_LABEL[estimate.band], "low": estimate.low, "high": estimate.high, "attempts": state.graded_attempts, "independent": state.independent_solved, "assisted": state.assisted_solved})
    hints = db.scalars(select(Hint).where(Hint.user_id == student_id, Hint.delivery == "shown").order_by(Hint.created_at.desc()).limit(15)).all()
    recent = db.scalars(select(Evaluation).where(Evaluation.user_id == student_id, Evaluation.kind == "submit").order_by(Evaluation.created_at.desc()).limit(15)).all()
    return {
        "id": student.id, "name": student.name, "metrics": analytics.learner_metrics(db, [student_id]), "topics": topics, "flags": analytics.learner_flags(db, student_id), "activity": analytics.activity_by_day(db, [student_id]),
        "hints": [_hint_row(h, titles.get(h.problem_id)).model_dump() for h in hints],
        "recent": [{"problem_id": e.problem_id, "title": titles.get(e.problem_id), "verdict": e.verdict, "passed": e.passed, "total": e.total, "at": e.created_at} for e in recent],
        "learning_gain": analytics.learning_gain(db, [student_id]), "is_synthetic": student.is_synthetic,
    }
