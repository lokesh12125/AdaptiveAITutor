#!/usr/bin/env python3
"""Build content/problems/bank.yaml and content/solutions/bank.yaml from the definitions in this folder.

Run from the repository root:  backend/.venv/bin/python scripts/problem_bank/build.py

Runs only this project's own trusted reference solutions, on your machine. Fails if a hand-written example
disagrees with its reference solution, or if a slug or title repeats an existing problem.
"""
from __future__ import annotations

import ast
import copy
import importlib
import io as stringio
import json
import signal
import sys
from contextlib import redirect_stdout
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from dsl import PROBLEMS  # noqa: E402

MODULES = ["foundations", "core_python", "algorithms", "structures", "advanced", "more_foundations", "more_algorithms", "more_structures", "more_advanced"]


class Timeout(Exception):
    pass


def _alarm(*_):
    raise Timeout


signal.signal(signal.SIGALRM, _alarm)


def encode(value):
    """Expected values, in the form the grader compares. See backend/app/grading.py."""
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return {"$set": sorted((encode(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value):
            return {k: encode(v) for k, v in value.items()}
        return {"$dict": sorted(([encode(k), encode(v)] for k, v in value.items()), key=lambda x: json.dumps(x[0], sort_keys=True))}
    return value


def as_args(raw):
    return list(raw) if isinstance(raw, tuple) else [raw]


def main_function(solution: str) -> ast.FunctionDef:
    functions = [node for node in ast.parse(solution).body if isinstance(node, ast.FunctionDef)]
    if not functions:
        raise ValueError("no function")
    return functions[-1]  # helpers come first, and the function the tests call comes last


def signature(node: ast.FunctionDef) -> str:
    return f"def {node.name}({ast.unparse(node.args)}):"


def run_function(solution, prelude, name, args):
    namespace: dict = {}
    if prelude:
        exec(prelude, namespace)
    exec(solution, namespace)
    signal.alarm(10)
    try:
        return namespace[name](*copy.deepcopy(args))
    finally:
        signal.alarm(0)


def run_expr(solution, prelude, expr):
    namespace: dict = {}
    exec(prelude or "", namespace)
    exec(solution, namespace)
    signal.alarm(10)
    try:
        return eval(expr, namespace)
    finally:
        signal.alarm(0)


def run_setup(solution, prelude, setup, expr):
    namespace: dict = {}
    exec(prelude or "", namespace)
    exec(solution, namespace)
    signal.alarm(10)
    try:
        exec(setup, namespace)
        return eval(expr, namespace)
    finally:
        signal.alarm(0)


def run_program(solution, stdin):
    lines = iter(stdin.split("\n"))

    def fake_input(prompt=""):
        try:
            return next(lines)
        except StopIteration as exc:
            raise EOFError from exc

    buffer = stringio.StringIO()
    signal.alarm(10)
    try:
        with redirect_stdout(buffer):
            exec(solution, {"input": fake_input, "__name__": "__main__"})
    finally:
        signal.alarm(0)
    return buffer.getvalue()


def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-9
    return encode(a) == encode(b)


def build(problem: dict) -> tuple[dict, str]:
    kind, slug = problem["kind"], problem["slug"]
    solution = problem["solution"]
    entry = {"slug": slug, "title": problem["title"], "unit": problem["unit"], "difficulty": problem["difficulty"], "pattern": problem["pattern"], "concepts": problem.get("concepts") or [problem["pattern"].lower().replace(" ", "-")], "description": problem["description"]}
    if problem.get("constraints"):
        entry["constraints"] = problem["constraints"]
    if problem.get("per_test_seconds"):
        entry["per_test_seconds"] = problem["per_test_seconds"]
    tests = []
    if kind == "io":
        entry["mode"] = "stdio"
        entry["starter_code"] = "# Read the input with input(), and print your answer.\n"
        for stdin, stdout in problem["ex"]:
            actual = run_program(solution, stdin)
            if actual.rstrip() != stdout.rstrip():
                raise ValueError(f"example {stdin!r}: wrote {stdout!r}, solution gives {actual!r}")
            tests.append({"stdin": stdin, "expected_stdout": actual})
        for stdin in problem["hid"]:
            tests.append({"stdin": stdin, "expected_stdout": run_program(solution, stdin)})
    elif kind == "class":
        entry["function_name"] = None
        entry["starter_code"] = problem["starter"].strip() + "\n"
        for setup, expr, expected in problem["ex"]:
            actual = run_setup(solution, problem.get("prelude"), setup, expr)
            if not same(actual, expected):
                raise ValueError(f"example {setup!r} / {expr!r}: wrote {expected!r}, solution gives {actual!r}")
            tests.append({"setup": setup, "expr": expr, "expected": encode(actual)})
        for setup, expr in problem["hid"]:
            tests.append({"setup": setup, "expr": expr, "expected": encode(run_setup(solution, problem.get("prelude"), setup, expr))})
    else:
        node = main_function(solution)
        entry["function_name"] = node.name
        entry["starter_code"] = f"{signature(node)}\n    # Write your solution here\n    pass\n"
        prelude = problem.get("prelude")
        if prelude:
            entry["prelude"] = prelude
        if kind == "fn":
            for raw, expected in problem["ex"]:
                args = as_args(raw)
                actual = run_function(solution, prelude, node.name, args)
                if not same(actual, expected):
                    raise ValueError(f"example {raw!r}: wrote {expected!r}, solution gives {actual!r}")
                tests.append({"args": copy.deepcopy(args), "expected": encode(actual)})
            for raw in problem["hid"]:
                args = as_args(raw)
                tests.append({"args": copy.deepcopy(args), "expected": encode(run_function(solution, prelude, node.name, args))})
        elif kind == "raw":
            for expr, expected in problem["ex"]:
                actual = run_expr(solution, prelude, expr)
                if not same(actual, expected):
                    raise ValueError(f"example {expr!r}: wrote {expected!r}, solution gives {actual!r}")
                tests.append({"expr": expr, "expected": encode(actual)})
            for expr in problem["hid"]:
                tests.append({"expr": expr, "expected": encode(run_expr(solution, prelude, expr))})
        else:
            for raw, expected in problem["ex"]:
                expr = problem["call"].format(*[repr(a) for a in as_args(raw)])
                actual = run_expr(solution, prelude, expr)
                if not same(actual, expected):
                    raise ValueError(f"example {raw!r}: wrote {expected!r}, solution gives {actual!r}")
                tests.append({"expr": expr, "expected": encode(actual)})
            for raw in problem["hid"]:
                expr = problem["call"].format(*[repr(a) for a in as_args(raw)])
                tests.append({"expr": expr, "expected": encode(run_expr(solution, prelude, expr))})
    if len(problem["ex"]) < 1:
        raise ValueError("needs at least one visible example")
    entry["public"] = len(problem["ex"])
    entry["tests"] = tests
    return entry, solution


def existing() -> tuple[set[str], set[str]]:
    slugs: set[str] = set()
    titles: set[str] = set()
    for row in json.loads((ROOT / "content/problems/legacy.json").read_text()) + yaml.safe_load((ROOT / "content/problems/authored.yaml").read_text()):
        slugs.add(row["slug"])
        titles.add(row["title"].lower())
    return slugs, titles


class Block(str):
    pass


yaml.SafeDumper.add_representer(Block, lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", str(value), style="|"))


def main() -> int:
    for name in MODULES:
        if (HERE / f"{name}.py").exists():
            importlib.import_module(name)
    slugs, titles = existing()
    entries, solutions, failures = [], {}, []
    for problem in PROBLEMS:
        slug, title = problem["slug"], problem["title"].lower()
        if slug in slugs or title in titles:
            failures.append(f"{slug}: slug or title is already used")
            continue
        slugs.add(slug)
        titles.add(title)
        try:
            entry, solution = build(problem)
        except Exception as exc:  # noqa: BLE001 - report every problem at once
            failures.append(f"{slug}: {type(exc).__name__}: {exc}")
            continue
        for key in ("description", "starter_code", "prelude"):
            if key in entry:
                entry[key] = Block(entry[key])
        entries.append(entry)
        solutions[slug] = Block(solution)
    if failures:
        print(f"{len(failures)} problem(s) failed:")
        print("\n".join(f"  {line}" for line in failures))
        return 1
    header = "# Generated by scripts/problem_bank/build.py. Edit the definitions there, not this file.\n"
    (ROOT / "content/problems/bank.yaml").write_text(header + yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=120))
    (ROOT / "content/solutions/bank.yaml").write_text(header + yaml.safe_dump(solutions, sort_keys=False, allow_unicode=True, width=120))
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["unit"]] = counts.get(entry["unit"], 0) + 1
    print(f"Built {len(entries)} problems:", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
