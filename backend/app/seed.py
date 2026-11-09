"""Load curriculum content, and optionally synthetic demonstration records. Safe to run repeatedly.

Synthetic data is generated from a fixed seed and marked as such in every table it touches.
It exists only so the demo shows retrieval and the teacher view, and it is never presented as evidence.
Usage: python -m app.seed            content, plus demo data when DEMO_MODE=true
       python -m app.seed --content  content only
"""
from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, select

from .config import settings
from .db import session_scope
from .models import (
    ClassMember,
    Classroom,
    CodeSnapshot,
    Diagnostic,
    Evaluation,
    Hint,
    InterventionCase,
    PipelineRun,
    Problem,
    ProblemSolution,
    ProblemTest,
    Recommendation,
    StateSnapshot,
    SurveyResponse,
    TopicState,
    Unit,
    User,
)
from .tutoring.retrieval import situation_vector, store

DIFFICULTY_SCORE = {"easy": 0.25, "medium": 0.5, "hard": 0.8}
DEMO_TEACHER_EMAIL = "demo-teacher@demo.invalid"


def load_content_files() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    root: Path = settings.content_path
    units = json.loads((root / "units.json").read_text())
    problems = json.loads((root / "problems" / "legacy.json").read_text())
    problems += yaml.safe_load((root / "problems" / "authored.yaml").read_text())
    solutions: dict[str, str] = {}
    for path in sorted((root / "solutions").glob("*.yaml")):
        solutions.update(yaml.safe_load(path.read_text()))
    return units, problems, solutions


def normalise_test(raw: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "stdio" or "stdin" in raw:
        return {"kind": "stdio", "payload": {"stdin": raw.get("stdin", "")}, "expected": raw.get("expected_stdout", raw.get("expected"))}
    if "expr" in raw:
        return {"kind": "expr", "payload": {"setup": raw.get("setup", ""), "expr": raw["expr"]}, "expected": raw.get("expected")}
    return {"kind": "args", "payload": {"args": raw.get("args", [])}, "expected": raw.get("expected")}


def seed_content() -> dict[str, int]:
    units, problems, solutions = load_content_files()
    with session_scope() as db:
        for unit in units:
            row = db.get(Unit, unit["id"]) or Unit(id=unit["id"])
            row.title, row.order_index, row.track, row.summary, row.optional, row.prerequisites, row.lessons = (
                unit["title"], unit["order"], unit["track"], unit["summary"], unit.get("optional", False), unit.get("prerequisites", []), unit.get("lessons", []),
            )
            db.add(row)
        db.flush()
        unit_order = {u["id"]: u["order"] for u in units}
        counters: dict[str, int] = {}
        for raw in problems:
            slug = raw["slug"]
            unit_id = raw["unit"]
            counters[unit_id] = counters.get(unit_id, 0) + 1
            row = db.get(Problem, slug) or Problem(id=slug)
            mode = raw.get("mode", "function")
            source = raw.get("source") or {"type": "curriculum", "name": "Project curriculum"}
            row.title, row.unit_id, row.difficulty, row.difficulty_score, row.concepts, row.mode = (
                raw["title"], unit_id, raw.get("difficulty"), DIFFICULTY_SCORE.get(raw.get("difficulty"), 0.5), raw.get("concepts", []), mode,
            )
            row.description, row.starter_code, row.function_name, row.prelude = raw["description"].strip(), raw["starter_code"], raw.get("function_name"), raw.get("prelude")
            row.per_test_seconds = float(raw.get("per_test_seconds", 2.0))
            row.source_type, row.source_name, row.source_note = source.get("type", "curriculum"), source.get("name"), source.get("note")
            row.recommended_first = bool(raw.get("recommended_first", False))
            row.order_index = unit_order[unit_id] * 1000 + {"easy": 0, "medium": 300, "hard": 600}.get(raw.get("difficulty"), 300) + counters[unit_id] - (100 if raw.get("recommended_first") else 0)
            db.add(row)
            db.flush()
            db.execute(delete(ProblemTest).where(ProblemTest.problem_id == slug))
            public = int(raw.get("public", 2))
            for index, test in enumerate(raw["tests"]):
                data = normalise_test(test, mode)
                db.add(ProblemTest(problem_id=slug, order_index=index, visibility="public" if index < public else "hidden", origin="curriculum", kind=data["kind"],
                                   payload=data["payload"], expected=data["expected"], compare=test.get("compare", "exact")))
            if slug in solutions:
                solution = db.get(ProblemSolution, slug) or ProblemSolution(problem_id=slug)
                solution.code = solutions[slug]
                db.add(solution)
    return {"units": len(units), "problems": len(problems), "solutions": len(solutions)}


STRATEGIES = {
    "syntax": ["syntax_pinpoint"], "runtime": ["error_tracing", "step_outline"], "timeout": ["termination_reasoning", "step_outline"], "resource": ["termination_reasoning"],
    "wrong_answer": ["trace_example", "boundary_check", "return_value", "step_outline"], "partial": ["boundary_check", "trace_example", "step_outline"],
}
ISSUES = {
    "syntax": ["syntax:missing_colon", "syntax:indentation", "syntax:unbalanced_bracket"], "runtime": ["runtime:IndexError", "runtime:TypeError", "runtime:KeyError", "runtime:NameError"],
    "timeout": ["timeout:loop_no_progress", "timeout:general"], "resource": ["resource:output"], "wrong_answer": ["logic:off_by_one", "logic:missing_return", "logic:general"], "partial": ["logic:edge_case", "logic:off_by_one"],
}


def seed_synthetic_cases(count: int = 400) -> int:
    """Generated with a plausible but invented rule. Labelled 'synthetic' and excluded when configured."""
    rng = random.Random(20261109)
    with session_scope() as db:
        unit_ids = list(db.scalars(select(Unit.id)).all())
        db.execute(delete(InterventionCase).where(InterventionCase.provenance == "synthetic"))
        cases = []
        for _ in range(count):
            category = rng.choice(list(STRATEGIES))
            mastery = rng.random()
            level = 2 if category == "syntax" else rng.choice([1, 2, 2, 3, 3, 4])
            ideal = 3 if mastery < 0.35 else (2 if mastery < 0.7 else 1)
            chance = 0.72 if abs(level - ideal) == 0 else (0.5 if abs(level - ideal) == 1 else 0.25)
            load = rng.choice([None, "low", "moderate", "high"])
            confusion = rng.choice([None, "low", "moderate", "high"])
            vector = situation_vector(mastery, rng.choice([None, 0.2, 0.5, 0.85]), confusion, load, rng.choice(["unknown", "steady", "stalled", "improving"]),
                                      rng.choice([0.25, 0.5, 0.8]), rng.randint(1, 6), rng.randint(0, 4), category)
            cases.append(InterventionCase(
                provenance="synthetic", unit_id=rng.choice(unit_ids), category=category, issue_key=rng.choice(ISSUES[category]), difficulty=rng.choice([0.25, 0.5, 0.8]), level=level,
                strategy=rng.choice(STRATEGIES[category]), outcome="progress" if rng.random() < chance else "no_progress", vector=vector,
            ))
        db.add_all(cases)
        db.flush()
        collection = store.collection()
        existing = collection.get(where={"provenance": "synthetic"}, include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
        for start in range(0, len(cases), 200):
            batch = cases[start : start + 200]
            collection.upsert(ids=[c.id for c in batch], embeddings=[c.vector for c in batch],
                              metadatas=[{"provenance": c.provenance, "category": c.category, "unit_id": c.unit_id} for c in batch])
    return count


def reindex_vectors() -> int:
    """Rebuild ChromaDB from PostgreSQL, which is the source of truth for cases."""
    with session_scope() as db:
        cases = db.scalars(select(InterventionCase)).all()
        for start in range(0, len(cases), 200):
            batch = cases[start : start + 200]
            store.collection().upsert(ids=[c.id for c in batch], embeddings=[c.vector for c in batch], metadatas=[{"provenance": c.provenance, "category": c.category, "unit_id": c.unit_id} for c in batch])
        return len(cases)


SYNTHETIC_NAMES = ["Asha (synthetic)", "Ben (synthetic)", "Chitra (synthetic)", "Dev (synthetic)", "Esha (synthetic)", "Farid (synthetic)", "Gita (synthetic)", "Hari (synthetic)"]


def seed_demo_class() -> dict[str, int]:
    """A clearly labelled synthetic class, so the teacher view can be seen without real student data."""
    rng = random.Random(77)
    now = datetime.now(UTC)
    with session_scope() as db:
        teacher = db.scalar(select(User).where(User.email == DEMO_TEACHER_EMAIL))
        if teacher:
            classroom = db.scalar(select(Classroom).where(Classroom.teacher_id == teacher.id, Classroom.is_synthetic.is_(True)))
            if classroom:
                return {"students": 0}
        else:
            teacher = User(email=DEMO_TEACHER_EMAIL, name="Demo Teacher", role="teacher", is_demo=True, is_synthetic=True, onboarding_completed=True, preferences={})
            db.add(teacher)
            db.flush()
        classroom = Classroom(name="Demo class (synthetic data)", teacher_id=teacher.id, join_code="DEMOCLASS", is_synthetic=True)
        db.add(classroom)
        db.flush()
        problems = db.scalars(select(Problem).where(Problem.owner_id.is_(None), Problem.unit_id.in_(["python-basics", "conditionals", "loops", "functions", "lists-dicts"])).order_by(Problem.order_index)).all()
        verdicts = [("accepted", 1.0), ("wrong_answer", 0.0), ("partial", 0.5), ("runtime_error", 0.0), ("syntax_error", 0.0)]
        issues = {"wrong_answer": "logic:off_by_one", "partial": "logic:edge_case", "runtime_error": "runtime:IndexError", "syntax_error": "syntax:missing_colon"}
        categories = {"wrong_answer": "wrong_answer", "partial": "partial", "runtime_error": "runtime", "syntax_error": "syntax", "accepted": "accepted"}
        for number, name in enumerate(SYNTHETIC_NAMES):
            skill = 0.2 + 0.09 * number
            student = User(email=f"synthetic-{number}@demo.invalid", name=name, role="student", is_demo=True, is_synthetic=True, onboarding_completed=True, preferences={})
            db.add(student)
            db.flush()
            db.add(ClassMember(class_id=classroom.id, user_id=student.id))
            topic_totals: dict[str, dict[str, float]] = {}
            for problem in rng.sample(problems, k=min(len(problems), 6 + number)):
                snapshot = CodeSnapshot(user_id=student.id, problem_id=problem.id, code="# synthetic record: no real code", code_hash=f"{student.id}{problem.id}"[:64])
                db.add(snapshot)
                db.flush()
                attempts = rng.randint(1, 4)
                moment = now - timedelta(days=rng.randint(0, 12), hours=rng.randint(0, 20))
                repeat = 0
                last_issue = None
                for attempt in range(attempts):
                    solved_now = attempt == attempts - 1 and rng.random() < skill + 0.35
                    verdict, ratio = ("accepted", 1.0) if solved_now else rng.choice(verdicts[1:])
                    moment += timedelta(minutes=rng.randint(2, 15))
                    total = 5
                    passed = int(total * ratio)
                    evaluation = Evaluation(user_id=student.id, problem_id=problem.id, snapshot_id=snapshot.id, kind="submit", idempotency_key=f"syn-{student.id[:10]}-{problem.id[:30]}-{attempt}", status="completed", verdict=verdict,
                                            passed=passed, total=total, public_results=[], internal_results=[], active_seconds=rng.randint(120, 900), created_at=moment, finished_at=moment, runner_backend="synthetic")
                    db.add(evaluation)
                    db.flush()
                    run = PipelineRun(user_id=student.id, problem_id=problem.id, evaluation_id=evaluation.id, snapshot_id=snapshot.id, trigger="submission", idempotency_key=f"syn-{evaluation.id}"[:64], correlation_id=evaluation.id, thread_id="synthetic", status="completed", created_at=moment, finished_at=moment)
                    db.add(run)
                    db.flush()
                    issue = "accepted" if solved_now else issues[verdict]
                    repeat = repeat + 1 if issue == last_issue else 1
                    last_issue = issue
                    db.add(Diagnostic(run_id=run.id, user_id=student.id, problem_id=problem.id, category=categories[verdict], issue_key=issue, repeat_count=repeat, confidence=0.7, data={"synthetic": True}, created_at=moment))
                    if not solved_now and rng.random() < 0.65:
                        db.add(Hint(run_id=run.id, user_id=student.id, problem_id=problem.id, unit_id=problem.unit_id, snapshot_id=snapshot.id, issue_key=issue, category=categories[verdict], level=rng.randint(1, min(4, attempt + 2)), strategy="trace_example",
                                    text="Synthetic record.", source="built_in", requested=rng.random() < 0.6, reason_student="Synthetic record.", reason_codes=["SYNTHETIC"], policy_version="synthetic", validation={}, outcome=rng.choice(["progress", "no_progress", "no_progress", "solved"]), outcome_at=moment, created_at=moment))
                    totals = topic_totals.setdefault(problem.unit_id, {"attempts": 0, "solved": 0})
                    totals["attempts"] += 1
                    totals["solved"] += 1 if solved_now else 0
                    if solved_now:
                        db.add(Recommendation(run_id=run.id, user_id=student.id, action="similar_independent", title="Synthetic", reason="Synthetic record.", reason_codes=["SYNTHETIC"], alternatives=[], created_at=moment))
            for unit_id, totals in topic_totals.items():
                mastery = min(0.95, skill * 0.6 + 0.1 + 0.1 * totals["solved"])
                db.add(TopicState(user_id=student.id, unit_id=unit_id, mastery=mastery, evidence_weight=totals["attempts"] * 0.7, graded_attempts=int(totals["attempts"]), solved_count=int(totals["solved"]), independent_solved=int(totals["solved"] // 2), assisted_solved=int(totals["solved"] - totals["solved"] // 2), version=1))
            if number % 2 == 0:
                db.add(SurveyResponse(user_id=student.id, usefulness=rng.randint(3, 5), clarity=rng.randint(3, 5), hint_adequacy=rng.randint(2, 5), adaptivity=rng.randint(2, 5)))
    _ = StateSnapshot
    return {"students": len(SYNTHETIC_NAMES)}


def main() -> None:
    result = seed_content()
    print(f"Content: {result}")
    if "--content" not in sys.argv and settings.demo_mode:
        print(f"Synthetic retrieval cases: {seed_synthetic_cases()}")
        print(f"Synthetic class: {seed_demo_class()}")
    print(f"Vectors in ChromaDB: {store.count()}")


if __name__ == "__main__":
    main()
