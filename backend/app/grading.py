"""Trusted grading. Compares sandbox-reported values with expected answers held only on this side.

Public results may show inputs and outputs. Hidden results expose only pass/fail and a broad category.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from .models import ProblemTest

FLOAT_TOLERANCE = 1e-9
FAILURE_PRIORITY = ["memory_limit", "timeout", "output_limit", "runtime_error", "missing_function", "wrong_answer"]


def canonical(value: Any) -> Any:
    """Tuple and list compare equal, matching how the exercises are written. Dict and set order is ignored."""
    if isinstance(value, dict):
        if "$tuple" in value:
            return [canonical(v) for v in value["$tuple"]]
        if "$set" in value:
            return {"$set": sorted((canonical(v) for v in value["$set"]), key=_sort_key)}
        if "$dict" in value:
            pairs = [[canonical(k), canonical(v)] for k, v in value["$dict"]]
            return {"$dict": sorted(pairs, key=lambda p: _sort_key(p[0]))}
        if any(k.startswith("$") for k in value):
            return value
        return {"$dict": sorted(([k, canonical(v)] for k, v in value.items()), key=lambda p: _sort_key(p[0]))}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value


def _sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if isinstance(actual, int) and isinstance(expected, int):
            return actual == expected
        return math.isclose(float(actual), float(expected), rel_tol=FLOAT_TOLERANCE, abs_tol=FLOAT_TOLERANCE)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(values_equal(a, e) for a, e in zip(actual, expected))
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual) != set(expected):
            return False
        return all(values_equal(actual[k], expected[k]) for k in actual)
    return actual == expected


def compare_values(actual: Any, expected: Any, mode: str = "exact") -> bool:
    a, e = canonical(actual), canonical(expected)
    if mode == "unordered" and isinstance(a, list) and isinstance(e, list):
        a, e = sorted(a, key=_sort_key), sorted(e, key=_sort_key)
    return values_equal(a, e)


def normalise_stdout(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").rstrip().split("\n"))


def display(value: Any, limit: int = 600) -> str:
    """Readable Python-like text for tagged values."""

    def fmt(v: Any) -> str:
        if isinstance(v, dict):
            if "$tuple" in v:
                inner = ", ".join(fmt(x) for x in v["$tuple"])
                return f"({inner},)" if len(v["$tuple"]) == 1 else f"({inner})"
            if "$set" in v:
                return "{" + ", ".join(fmt(x) for x in v["$set"]) + "}" if v["$set"] else "set()"
            if "$dict" in v:
                return "{" + ", ".join(f"{fmt(k)}: {fmt(x)}" for k, x in v["$dict"]) + "}"
            if "$repr" in v:
                return str(v["$repr"])
            if "$float" in v:
                return str(v["$float"])
            if "$bigint" in v:
                return str(v["$bigint"])
            if "$opaque" in v:
                return f"<{v['$opaque']} object>"
            if "$bytes" in v:
                return f"bytes:{v['$bytes']}"
            return "{" + ", ".join(f"{k!r}: {fmt(x)}" for k, x in v.items()) + "}"
        if isinstance(v, list):
            return "[" + ", ".join(fmt(x) for x in v) + "]"
        return repr(v)

    text = fmt(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parameter_names(starter_code: str | None, function_name: str | None) -> list[str]:
    """The parameter names of the function the tests call, read from the starter code."""
    import ast

    try:
        for node in ast.parse(starter_code or "").body:
            if isinstance(node, ast.FunctionDef) and (not function_name or node.name == function_name):
                return [arg.arg for arg in node.args.args]
    except (SyntaxError, ValueError):
        pass
    return []


def describe_input(test: ProblemTest, function_name: str | None) -> str:
    payload = test.payload or {}
    if test.kind == "args":
        args = ", ".join(display(a, 200) for a in payload.get("args", []))
        return f"{function_name or 'solution'}({args})"
    if test.kind == "expr":
        setup = (payload.get("setup") or "").strip()
        return f"{setup}\n{payload.get('expr')}" if setup else str(payload.get("expr"))
    return payload.get("stdin") or "(no input)"


@dataclass
class Graded:
    verdict: str
    passed: int
    total: int
    public_results: list[dict[str, Any]]
    internal_results: list[dict[str, Any]]


CATEGORY_LABEL = {
    "wrong_answer": "Wrong answer",
    "runtime_error": "Error while running",
    "timeout": "Took too long",
    "memory_limit": "Used too much memory",
    "output_limit": "Printed too much output",
    "missing_function": "Function not found",
    "syntax_error": "Syntax error",
    "crashed": "Program crashed",
    "skipped": "Not run",
}


def _status_to_category(status: str) -> str:
    return {
        "exception": "runtime_error", "syntax_error": "syntax_error", "timeout": "timeout",
        "output_limit": "output_limit", "memory_limit": "memory_limit", "missing_function": "missing_function",
        "value_too_large": "wrong_answer", "invalid_result": "runtime_error", "crashed": "runtime_error",
        "skipped_time_budget": "skipped", "bad_test": "skipped",
    }.get(status, "runtime_error")


def grade_test(test: ProblemTest, outcome: dict[str, Any]) -> tuple[bool, str]:
    status = outcome.get("status")
    if status != "ok":
        return False, _status_to_category(str(status))
    if test.compare == "completes":
        return True, "passed"
    if test.kind == "stdio":
        expected = test.expected if isinstance(test.expected, str) else ""
        return normalise_stdout(outcome.get("stdout", "")) == normalise_stdout(expected), "wrong_answer"
    return compare_values(outcome.get("value"), test.expected, test.compare), "wrong_answer"


def grade(tests: list[ProblemTest], outcomes: list[dict[str, Any]], function_name: str | None) -> Graded:
    by_id = {o.get("id"): o for o in outcomes}
    public: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    passed = 0
    categories: list[str] = []
    hidden_number = 0
    public_number = 0
    for test in tests:
        outcome = by_id.get(test.id, {"status": "invalid_result"})
        ok, category = grade_test(test, outcome)
        passed += 1 if ok else 0
        if not ok:
            categories.append(category)
        error = outcome.get("error")
        internal.append({
            "test_id": test.id, "visibility": test.visibility, "passed": ok, "category": "passed" if ok else category,
            "status": outcome.get("status"), "value": outcome.get("value"), "expected": test.expected,
            "stdout": (outcome.get("stdout") or "")[:4000], "error": error, "phase": outcome.get("phase"),
            "duration_ms": outcome.get("duration_ms", 0), "kind": test.kind,
            "input": describe_input(test, function_name), "origin": test.origin, "compare": test.compare,
            "args": (test.payload or {}).get("args") if test.kind == "args" else None,
        })
        if test.visibility == "public":
            public_number += 1
            row: dict[str, Any] = {
                "id": test.id, "name": test.label or f"Example {public_number}", "visibility": "public",
                "passed": ok, "category": "passed" if ok else category, "origin": test.origin,
                "input": describe_input(test, function_name),
                "stdout": (outcome.get("stdout") or "")[:4000], "stderr": (outcome.get("stderr") or "")[:2000],
                "truncated": bool(outcome.get("truncated")), "duration_ms": outcome.get("duration_ms", 0),
            }
            if test.compare == "completes":
                row["expected"] = "Finishes within the time limit"
                row["actual"] = "Finished" if ok else CATEGORY_LABEL.get(category, category)
            elif test.kind == "stdio":
                row["expected"] = test.expected if isinstance(test.expected, str) else ""
                row["actual"] = outcome.get("stdout", "")[:4000]
            else:
                row["expected"] = display(test.expected)
                row["actual"] = display(outcome.get("value")) if outcome.get("status") == "ok" else None
            if error:
                row["error"] = {"type": error.get("type"), "message": error.get("message"), "line": error.get("line"),
                                "column": error.get("column")}
            if outcome.get("status") == "missing_function":
                row["error"] = {"type": "MissingFunction", "message": f"Could not find a function named {outcome.get('name')}.", "line": None}
            public.append(row)
        else:
            hidden_number += 1
            public.append({
                "id": test.id, "name": f"Hidden test {hidden_number}", "visibility": "hidden", "passed": ok,
                "category": "passed" if ok else category, "origin": test.origin,
            })
    total = len(tests)
    return Graded(_verdict(passed, total, categories), passed, total, public, internal)


def _verdict(passed: int, total: int, categories: list[str]) -> str:
    if total == 0:
        return "no_tests"
    if passed == total:
        return "accepted"
    if "syntax_error" in categories:
        return "syntax_error"
    if passed > 0:
        return "partial"
    for category in FAILURE_PRIORITY:
        if category in categories:
            return category
    return "wrong_answer"


def dominant_failure(internal: list[dict[str, Any]]) -> str | None:
    categories = [r["category"] for r in internal if not r["passed"]]
    for category in FAILURE_PRIORITY:
        if category in categories:
            return category
    return categories[0] if categories else None
