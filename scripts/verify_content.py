#!/usr/bin/env python3
"""Check every curriculum problem through the real execution service.

For each problem: the reference solution must pass all tests, and the unmodified starter code must not.
Run from backend/ with its virtualenv:  python ../scripts/verify_content.py [problem-id ...]
"""
import sys
import time
import uuid

from sqlalchemy import select

from app.db import session_scope
from app.grading import grade
from app.models import Problem, ProblemSolution
from app.runner_client import runner


def job_for(problem, code):
    tests = [{"id": t.id, "kind": t.kind, "args": (t.payload or {}).get("args", []), "setup": (t.payload or {}).get("setup"), "expr": (t.payload or {}).get("expr"), "stdin": (t.payload or {}).get("stdin")} for t in problem.tests]
    return {"job_id": uuid.uuid4().hex, "language": "python", "code": code, "prelude": problem.prelude, "function_name": problem.function_name, "tests": tests,
            "limits": {"per_test_seconds": 3, "total_seconds": 25, "memory_mb": 192, "output_kb": 64}}


def execute(job):
    """The service may say it is busy under load, so ask again rather than reporting a false failure."""
    for _ in range(40):
        result = runner.execute(job)
        if result.status != "busy":
            return result
        time.sleep(0.5)
    return result


def main() -> int:
    failures = 0
    checked = 0
    with session_scope() as db:
        problems = db.scalars(select(Problem).where(Problem.owner_id.is_(None), Problem.archived.is_(False)).order_by(Problem.order_index)).all()
        if len(sys.argv) > 1:  # check only the problems named on the command line
            problems = [p for p in problems if p.id in sys.argv[1:]]
        for problem in problems:
            solution = db.get(ProblemSolution, problem.id)
            if not solution:
                print(f"NO SOLUTION  {problem.id}")
                failures += 1
                continue
            result = execute(job_for(problem, solution.code))
            if result.status != "completed":
                print(f"RUNNER {result.status}: {problem.id} {result.message}")
                return 2
            graded = grade(list(problem.tests), result.results, problem.function_name)
            if graded.verdict != "accepted":
                failures += 1
                print(f"SOLUTION FAILS {problem.id}: {graded.passed}/{graded.total}")
                for row in graded.internal_results:
                    if not row["passed"]:
                        print(f"   {row['input'][:90]!r} got={row['value']!r} want={row['expected']!r} status={row['status']} err={(row.get('error') or {}).get('message')}")
                        break
            starter = execute(job_for(problem, problem.starter_code))
            starter_graded = grade(list(problem.tests), starter.results, problem.function_name)
            if starter_graded.verdict == "accepted":
                failures += 1
                print(f"STARTER PASSES {problem.id}")
            checked += 1
    print(f"Checked {checked} problems, {failures} problem(s) failed verification.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
