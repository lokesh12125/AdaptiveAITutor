"""Add Question: paste or look up a problem, review it, then practise with the same tutoring workflow."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ratelimit
from ..config import settings
from ..db import get_db
from ..errors import ApiError, not_found
from ..imports import fetcher, parser, sources, testgen
from ..models import Problem, ProblemTest, Unit, User, utcnow
from ..schemas import (
    GenerateTestsIn,
    ImportDraft,
    ImportExample,
    ImportOut,
    LookupIn,
    LookupOut,
    ParseIn,
    SaveImportIn,
    TestCase,
    TestsOut,
)
from ..security import current_user

router = APIRouter(prefix="/api/imports", tags=["imports"])
SCORE = {"easy": 0.25, "medium": 0.5, "hard": 0.8}
DEFAULT_UNIT = "arrays-two-pointers"


@router.post("/parse", response_model=ImportDraft)
def parse(payload: ParseIn, user: User = Depends(current_user)) -> ImportDraft:
    ratelimit.check(f"import:{user.id}", settings.rate_import_per_minute)
    draft = parser.parse_problem_text(payload.text)
    draft.starter_code = parser.generate_starter(draft)
    # Attribution comes from the link the learner gave. Nothing is fetched here.
    if payload.source_url:
        name = sources.source_name_for(payload.source_url)
        if name is None:
            raise ApiError(422, "invalid_source_url", "That source link does not look like a web address.")
        draft.source_url, draft.source_name = fetcher.normalise_url(payload.source_url), name
    draft.unit_id = payload.unit_id or draft.unit_id
    draft.learner_notes = (payload.notes or "").strip() or None
    draft.extracted_fields = sources._extracted_fields(draft)
    return draft


@router.post("/lookup", response_model=LookupOut)
def lookup(payload: LookupIn, user: User = Depends(current_user)) -> LookupOut:
    ratelimit.check(f"import:{user.id}", settings.rate_import_per_minute)
    return sources.lookup(payload.query)


@router.post("/generate-tests", response_model=TestsOut)
def generate(payload: GenerateTestsIn, user: User = Depends(current_user)) -> TestsOut:
    ratelimit.check(f"import:{user.id}", settings.rate_import_per_minute)
    tests, notes = testgen.generate_tests(payload.draft)
    return TestsOut(tests=tests, notes=notes)


def _validate_draft(db: Session, draft: ImportDraft) -> str:
    problems = []
    if len(draft.title.strip()) < 3:
        problems.append({"field": "title", "message": "Please give the question a title."})
    if len(draft.description.strip()) < 15:
        problems.append({"field": "description", "message": "Please add the problem description."})
    if draft.mode == "function" and not draft.function_name:
        problems.append({"field": "function_name", "message": "Please name the function the tests should call."})
    if draft.source_url and not sources.source_name_for(draft.source_url):
        problems.append({"field": "source_url", "message": "The source link does not look like a web address."})
    if problems:
        raise ApiError(422, "invalid_question", "A few details are needed before saving.", details=problems)
    unit = draft.unit_id if draft.unit_id and db.get(Unit, draft.unit_id) else DEFAULT_UNIT
    return unit


def _apply(problem: Problem, draft: ImportDraft, unit_id: str) -> None:
    problem.title, problem.description, problem.constraints = draft.title.strip(), draft.description.strip(), draft.constraints
    problem.input_format, problem.output_format, problem.difficulty = draft.input_format, draft.output_format, draft.difficulty
    problem.difficulty_score = SCORE.get(draft.difficulty or "", 0.5)
    problem.concepts, problem.unit_id, problem.mode = draft.tags, unit_id, draft.mode
    problem.function_name = draft.function_name if draft.mode == "function" else None
    problem.starter_code = parser.generate_starter(draft)
    problem.source_type, problem.source_name, problem.source_url, problem.source_retrieved_at = "imported", draft.source_name or "Added by you", draft.source_url, draft.source_retrieved_at
    problem.learner_notes = (draft.learner_notes or "").strip() or None


def _replace_tests(problem: Problem, tests: list[TestCase]) -> None:
    problem.tests.clear()
    for index, test in enumerate(tests):
        payload = {"args": test.args or []} if test.kind == "args" else {"stdin": test.stdin or ""}
        problem.tests.append(ProblemTest(
            order_index=index, visibility="public", origin=test.origin, category=test.category, label=test.label, kind=test.kind, payload=payload, expected=test.expected,
            compare=test.compare, needs_expected=test.needs_expected, enabled=test.enabled,
        ))


@router.post("", response_model=ImportOut, status_code=201)
def save_import(payload: SaveImportIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ImportOut:
    ratelimit.check(f"import:{user.id}", settings.rate_import_per_minute)
    unit_id = _validate_draft(db, payload.draft)
    testgen.validate_tests(payload.draft, payload.tests)
    problem = Problem(id=f"imp-{uuid.uuid4().hex[:16]}", owner_id=user.id, title="", unit_id=unit_id, description="", starter_code="", order_index=900000)
    _apply(problem, payload.draft, unit_id)
    _replace_tests(problem, payload.tests)
    db.add(problem)
    db.commit()
    return _to_out(problem)


def _own(db: Session, problem_id: str, user: User) -> Problem:
    problem = db.get(Problem, problem_id)
    if not problem or problem.owner_id != user.id or problem.source_type != "imported":
        raise not_found("That question")
    return problem


def _to_out(problem: Problem) -> ImportOut:
    tests = [
        TestCase(id=t.id, label=t.label, origin=t.origin, category=t.category, kind=t.kind, args=(t.payload or {}).get("args") if t.kind == "args" else None, stdin=(t.payload or {}).get("stdin") if t.kind == "stdio" else None,
                 expected=t.expected, compare=t.compare, needs_expected=t.needs_expected, enabled=t.enabled)
        for t in problem.tests
    ]
    parameters: list[str] = []
    if problem.mode == "function" and problem.function_name:
        import ast

        try:
            for node in ast.parse(problem.starter_code).body:
                if isinstance(node, ast.FunctionDef) and node.name == problem.function_name:
                    parameters = [a.arg for a in node.args.args]
        except SyntaxError:
            parameters = []
    draft = ImportDraft(
        title=problem.title, description=problem.description, constraints=problem.constraints, input_format=problem.input_format, output_format=problem.output_format, difficulty=problem.difficulty, tags=problem.concepts or [], unit_id=problem.unit_id,
        mode=problem.mode, function_name=problem.function_name, parameters=parameters, starter_code=problem.starter_code, examples=[], source_name=problem.source_name, source_url=problem.source_url, source_retrieved_at=problem.source_retrieved_at, learner_notes=problem.learner_notes,
    )
    return ImportOut(id=problem.id, draft=draft, tests=tests)


@router.get("/{problem_id}", response_model=ImportOut)
def get_import(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ImportOut:
    return _to_out(_own(db, problem_id, user))


@router.put("/{problem_id}", response_model=ImportOut)
def update_import(problem_id: str, payload: SaveImportIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ImportOut:
    problem = _own(db, problem_id, user)
    unit_id = _validate_draft(db, payload.draft)
    testgen.validate_tests(payload.draft, payload.tests)
    _apply(problem, payload.draft, unit_id)
    _replace_tests(problem, payload.tests)
    problem.updated_at = utcnow()  # earlier results were produced by the old tests, so they must not be reused
    db.commit()
    return _to_out(problem)


@router.delete("/{problem_id}", status_code=204)
def delete_import(problem_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    db.delete(_own(db, problem_id, user))
    db.commit()
    return Response(status_code=204)


_ = (ImportExample, Optional, select)
