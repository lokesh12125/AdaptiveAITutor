from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..analytics import BAND_LABEL
from ..db import get_db
from ..errors import not_found
from ..grading import describe_input, display
from ..models import Evaluation, Problem, TopicState, Unit, User
from ..schemas import (
    ExampleOut,
    LessonOut,
    PathOut,
    ProblemDetail,
    ProblemSummary,
    UnitDetail,
    UnitOption,
    UnitPathItem,
)
from ..security import current_user
from ..tutoring import cognitive, planner
from ..tutoring.nodes import load_planner_views

router = APIRouter(prefix="/api", tags=["content"])
LANGUAGES = ["python"]  # only languages with working execution are ever listed


def visible_problem(db: Session, problem_id: str, user: User) -> Problem:
    problem = db.get(Problem, problem_id)
    if not problem or problem.archived or (problem.owner_id and problem.owner_id != user.id):
        raise not_found("That problem")
    return problem


def statuses(db: Session, user_id: str) -> tuple[set[str], set[str]]:
    rows = db.execute(select(Evaluation.problem_id, Evaluation.verdict).where(Evaluation.user_id == user_id, Evaluation.kind == "submit", Evaluation.verdict.notin_(["service_failure", "cancelled"]))).all()
    return {p for p, v in rows if v == "accepted"}, {p for p, _ in rows}


def to_summary(problem: Problem, unit_title: str, solved: set[str], attempted: set[str], user: User) -> ProblemSummary:
    status = "solved" if problem.id in solved else ("in_progress" if problem.id in attempted else "not_started")
    return ProblemSummary(id=problem.id, title=problem.title, unit_id=problem.unit_id, unit_title=unit_title, difficulty=problem.difficulty, concepts=problem.concepts or [], languages=LANGUAGES, status=status,
                          source_type=problem.source_type, source_name=problem.source_name, is_mine=problem.owner_id == user.id, recommended_first=problem.recommended_first)


def to_detail(db: Session, problem: Problem, user: User) -> ProblemDetail:
    unit = db.get(Unit, problem.unit_id)
    tests = [t for t in problem.tests if t.enabled and not t.needs_expected]
    examples = []
    for number, test in enumerate((t for t in tests if t.visibility == "public"), start=1):
        if test.compare == "completes":
            expected = "Finishes within the time limit"
        elif test.kind == "stdio":
            expected = test.expected if isinstance(test.expected, str) else None
        else:
            expected = display(test.expected)
        examples.append(ExampleOut(name=test.label or f"Example {number}", input=describe_input(test, problem.function_name), expected=expected, origin=test.origin))
    return ProblemDetail(
        id=problem.id, title=problem.title, unit_id=problem.unit_id, unit_title=unit.title if unit else problem.unit_id, difficulty=problem.difficulty, concepts=problem.concepts or [], languages=LANGUAGES, mode=problem.mode,
        description=problem.description, constraints=problem.constraints, input_format=problem.input_format, output_format=problem.output_format, starter_code=problem.starter_code, function_name=problem.function_name,
        prelude=problem.prelude, per_test_seconds=problem.per_test_seconds, examples=examples, hidden_test_count=sum(1 for t in tests if t.visibility == "hidden"), source_type=problem.source_type, source_name=problem.source_name,
        source_url=problem.source_url, source_note=problem.source_note, source_retrieved_at=problem.source_retrieved_at, is_mine=problem.owner_id == user.id,
    )


@router.get("/units/options", response_model=list[UnitOption])
def unit_options(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[UnitOption]:
    return [UnitOption(id=u.id, title=u.title) for u in db.scalars(select(Unit).order_by(Unit.order_index)).all()]


@router.get("/problems", response_model=list[ProblemSummary])
def list_problems(
    q: str | None = Query(default=None, max_length=80), unit: str | None = Query(default=None, max_length=64), difficulty: str | None = Query(default=None, pattern="^(easy|medium|hard)$"),
    status: str | None = Query(default=None, pattern="^(not_started|in_progress|solved)$"), mine: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user),
) -> list[ProblemSummary]:
    query = select(Problem).where(Problem.archived.is_(False), (Problem.owner_id.is_(None)) | (Problem.owner_id == user.id)).order_by(Problem.order_index, Problem.created_at)
    if unit:
        query = query.where(Problem.unit_id == unit)
    if difficulty:
        query = query.where(Problem.difficulty == difficulty)
    if mine:
        query = query.where(Problem.owner_id == user.id)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(func.lower(Problem.title).like(like) | func.lower(Problem.description).like(like) | func.lower(func.array_to_string(Problem.concepts, " ")).like(like))
    titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    solved, attempted = statuses(db, user.id)
    items = [to_summary(p, titles.get(p.unit_id, p.unit_id), solved, attempted, user) for p in db.scalars(query).all()]
    return [i for i in items if i.status == status] if status else items


@router.get("/problems/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ProblemDetail:
    return to_detail(db, visible_problem(db, problem_id, user), user)


def _band(value: float, evidence: float) -> tuple[str, float, float]:
    estimate = cognitive.mastery_estimate(value, evidence, False, "")
    return estimate.band, estimate.low, estimate.high


def recommendation_for(db: Session, user: User) -> planner.PlanOutput:
    units, problems = load_planner_views(db, user)
    return planner.plan(planner.PlannerInput(units=units, problems=problems, goal=user.goal, experience=user.experience_level))


@router.get("/path", response_model=PathOut)
def learning_path(db: Session = Depends(get_db), user: User = Depends(current_user)) -> PathOut:
    units = db.scalars(select(Unit).order_by(Unit.order_index)).all()
    states = {s.unit_id: s for s in db.scalars(select(TopicState).where(TopicState.user_id == user.id)).all()}
    solved, attempted = statuses(db, user.id)
    problems = db.execute(select(Problem.id, Problem.unit_id).where(Problem.archived.is_(False), Problem.owner_id.is_(None))).all()
    per_unit: dict[str, list[str]] = {}
    for pid, uid in problems:
        per_unit.setdefault(uid, []).append(pid)
    plan = recommendation_for(db, user)
    items: list[UnitPathItem] = []
    masteries = {u: (s.mastery, s.evidence_weight) for u, s in states.items()}
    current_unit = None
    for unit in units:
        state = states.get(unit.id)
        ids = per_unit.get(unit.id, [])
        solved_count = sum(1 for i in ids if i in solved)
        started = any(i in attempted for i in ids)
        band, low, high = _band(state.mastery, state.evidence_weight) if state else ("not_enough_evidence", 0.0, 1.0)
        weak_prereq = any(p in masteries and masteries[p][1] >= 0.5 and masteries[p][0] < planner.POLICY["prerequisite_gap"] for p in unit.prerequisites or [])
        unstarted_prereq = any(p not in masteries for p in unit.prerequisites or [])
        if plan.unit_id == unit.id:
            ui_state = "recommended"
            current_unit = unit.id
        elif state and state.mastery >= planner.POLICY["advance_mastery"] and state.independent_solved >= planner.POLICY["advance_min_independent"]:
            ui_state = "completed"
        elif started:
            ui_state = "in_progress"
        elif weak_prereq or unstarted_prereq:
            ui_state = "needs_foundations"
        else:
            ui_state = "available"
        note = BAND_LABEL[band] if band != "not_enough_evidence" else ("Not started" if not started else "Not enough evidence yet")
        items.append(UnitPathItem(id=unit.id, title=unit.title, order=unit.order_index, track=unit.track, optional=unit.optional, summary=unit.summary, prerequisites=unit.prerequisites or [], problems_total=len(ids), problems_solved=solved_count,
                                  state=ui_state, band=band, mastery_low=low if state else None, mastery_high=high if state else None, evidence_note=note))
    return PathOut(units=items, recommendation=plan.model_dump(), current_unit_id=current_unit)


@router.get("/units/{unit_id}", response_model=UnitDetail)
def unit_detail(unit_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> UnitDetail:
    unit = db.get(Unit, unit_id)
    if not unit:
        raise not_found("That topic")
    titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    problems = db.scalars(select(Problem).where(Problem.unit_id == unit_id, Problem.archived.is_(False), (Problem.owner_id.is_(None)) | (Problem.owner_id == user.id)).order_by(Problem.order_index).options(selectinload(Problem.tests))).all()
    solved, attempted = statuses(db, user.id)
    return UnitDetail(id=unit.id, title=unit.title, summary=unit.summary, track=unit.track, optional=unit.optional, prerequisites=[{"id": p, "title": titles.get(p, p)} for p in unit.prerequisites or []],
                      lessons=[LessonOut(**lesson) for lesson in unit.lessons or []], problems=[to_summary(p, unit.title, solved, attempted, user) for p in problems])
