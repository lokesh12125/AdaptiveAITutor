"""Every curriculum problem is checked in the real sandbox. Takes about a minute."""
import uuid

from sqlalchemy import select

from app.db import session_scope
from app.grading import grade
from app.models import Problem, ProblemSolution, Unit
from app.runner_client import runner


def _job(problem, code):
    tests = [{"id": t.id, "kind": t.kind, "args": (t.payload or {}).get("args", []), "setup": (t.payload or {}).get("setup"), "expr": (t.payload or {}).get("expr"), "stdin": (t.payload or {}).get("stdin")} for t in problem.tests]
    return {"job_id": uuid.uuid4().hex, "code": code, "prelude": problem.prelude, "function_name": problem.function_name, "tests": tests, "limits": {"per_test_seconds": 3, "total_seconds": 25, "memory_mb": 192, "output_kb": 64}}


def test_reference_solutions_pass_and_starters_do_not(app_ready):
    wrong, starter_passing = [], []
    with session_scope() as db:
        problems = db.scalars(select(Problem).where(Problem.owner_id.is_(None))).all()
        assert len(problems) >= 90
        for problem in problems:
            solution = db.get(ProblemSolution, problem.id)
            assert solution, f"{problem.id} has no reference solution"
            result = runner.execute(_job(problem, solution.code))
            assert result.status == "completed", result.message
            if grade(list(problem.tests), result.results, problem.function_name).verdict != "accepted":
                wrong.append(problem.id)
            start = runner.execute(_job(problem, problem.starter_code))
            if grade(list(problem.tests), start.results, problem.function_name).verdict == "accepted":
                starter_passing.append(problem.id)
    assert wrong == [] and starter_passing == []


def test_curriculum_structure(app_ready):
    with session_scope() as db:
        units = {u.id: u for u in db.scalars(select(Unit)).all()}
        problems = db.scalars(select(Problem).where(Problem.owner_id.is_(None))).all()
        for unit in units.values():
            assert all(p in units for p in unit.prerequisites), unit.id
            assert unit.lessons, f"{unit.id} has no lessons"
            assert sum(1 for p in problems if p.unit_id == unit.id) >= 3, f"{unit.id} needs at least 3 problems"
        for problem in problems:
            assert any(t.visibility == "public" for t in problem.tests), f"{problem.id} has no public example"
            assert problem.difficulty in ("easy", "medium", "hard")
        assert sum(1 for p in problems if p.recommended_first) == 1


def test_prerequisites_form_no_cycle(app_ready):
    with session_scope() as db:
        graph = {u.id: list(u.prerequisites or []) for u in db.scalars(select(Unit)).all()}
    done, visiting = set(), set()

    def visit(node):
        assert node not in visiting, f"cycle through {node}"
        if node in done:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.discard(node)
        done.add(node)

    for node in graph:
        visit(node)
