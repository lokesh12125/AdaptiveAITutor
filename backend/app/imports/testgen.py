"""Test generation for imported questions.

Example-based tests come straight from the learner's pasted text. Generated tests propose *inputs*.
A correct answer cannot be known reliably without a trusted solution, so generated tests are marked
"needs expected output" and stay disabled until the learner supplies one. The exception is a large-input
check, which only requires finishing in time. Generated tests are never the platform's hidden tests.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..errors import ApiError
from ..schemas import ImportDraft, TestCase

MAX_LARGE_ITEMS = 20000
MAX_TEST_BYTES = 256 * 1024
_NUM = r"(-?\s*\d[\d,]*(?:\s*(?:\^|\*\*)\s*\d+)?(?:\s*[xX*×]\s*10\s*\^?\s*\d+)?)"
_BOUND = re.compile(_NUM + r"\s*(?:<=|≤|<)\s*([A-Za-z_][\w.\[\]]*(?:\.length|\.size\(\))?|\|[A-Za-z_]\w*\|)\s*(?:<=|≤|<)\s*" + _NUM)


def _to_int(text: str) -> int | None:
    cleaned = text.replace(" ", "").replace(",", "")
    try:
        if "^" in cleaned or "**" in cleaned:
            base, exponent = re.split(r"\^|\*\*", cleaned)
            if base.endswith(("x10", "X10", "*10", "×10")):
                return int(float(base[:-3]) * 10 ** int(exponent))
            return int(base) ** int(exponent)
        return int(cleaned)
    except ValueError:
        return None


def parse_bounds(constraints: str | None) -> dict[str, tuple[int, int]]:
    bounds: dict[str, tuple[int, int]] = {}
    for low, name, high in _BOUND.findall(constraints or ""):
        lo, hi = _to_int(low), _to_int(high)
        if lo is None or hi is None:
            continue
        key = name.strip("|")
        key = re.sub(r"\[.*?\]", "", key)
        if ".length" in name or ".size" in name or name.startswith("|"):
            key = key.split(".")[0] + ".length"
        bounds[key] = (lo, hi)
    return bounds


def _case(args: list[Any], label: str, category: str, compare: str = "exact", needs: bool = True) -> TestCase:
    return TestCase(label=label, origin="generated", category=category, kind="args", args=args, expected=None, compare=compare, needs_expected=needs, enabled=not needs)


def example_tests(draft: ImportDraft) -> list[TestCase]:
    tests: list[TestCase] = []
    for index, example in enumerate(draft.examples, start=1):
        if draft.mode == "function" and example.args is not None:
            tests.append(TestCase(label=f"Example {index}", origin="example", category="normal", kind="args", args=example.args, expected=example.expected, needs_expected=False, enabled=True))
        elif draft.mode == "stdio" and example.stdin is not None:
            tests.append(TestCase(label=f"Example {index}", origin="example", category="normal", kind="stdio", stdin=example.stdin, expected=example.expected_stdout, needs_expected=example.expected_stdout is None, enabled=example.expected_stdout is not None))
    return tests


def _vary_position(base: list[Any], position: int, value: Any) -> list[Any]:
    return [value if i == position else item for i, item in enumerate(base)]


def generate_tests(draft: ImportDraft) -> tuple[list[TestCase], list[str]]:
    tests = example_tests(draft)
    notes = ["Generated tests are suggestions. They are not the original platform's hidden tests."]
    samples = [e.args for e in draft.examples if e.args is not None]
    if draft.mode == "stdio":
        for category, label in (("minimal", "Smallest allowed input"), ("boundary", "Largest allowed input"), ("repeated", "Repeated values")):
            tests.append(TestCase(label=f"{label}: fill this in", origin="generated", category=category, kind="stdio", stdin="", expected=None, needs_expected=True, enabled=False))
        notes.append("Inputs for programs that read from standard input depend on the format, so these need you to fill them in.")
        return tests, notes
    if not samples:
        notes.append("No parsed examples were found, so input shapes are unknown. Add a test by hand to continue.")
        return tests, notes

    base = samples[0]
    names = draft.parameters if len(draft.parameters) == len(base) else [f"arg{i + 1}" for i in range(len(base))]
    bounds = parse_bounds(draft.constraints)
    seen: set[str] = {json.dumps(t.args, sort_keys=True, default=str) for t in tests if t.args is not None}

    def add(case: TestCase) -> None:
        key = json.dumps(case.args, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            tests.append(case)

    for position, (name, value) in enumerate(zip(names, base)):
        value_bounds = bounds.get(name) or bounds.get(f"{name}[i]")
        length_bounds = bounds.get(f"{name}.length")
        if isinstance(value, bool):
            add(_case(_vary_position(base, position, not value), f"{name} flipped", "normal"))
        elif isinstance(value, int):
            low, high = value_bounds if value_bounds else (None, None)
            if low is not None:
                add(_case(_vary_position(base, position, low), f"{name} at its smallest allowed value", "boundary"))
                add(_case(_vary_position(base, position, high), f"{name} at its largest allowed value", "boundary"))
                if low < 0:
                    add(_case(_vary_position(base, position, -1), f"{name} negative", "negative"))
            else:
                add(_case(_vary_position(base, position, 0), f"{name} is zero", "boundary"))
                add(_case(_vary_position(base, position, 1), f"{name} is one", "boundary"))
                add(_case(_vary_position(base, position, -abs(value) - 1), f"{name} negative, if the task allows it", "negative"))
        elif isinstance(value, str):
            if not length_bounds or length_bounds[0] == 0:
                add(_case(_vary_position(base, position, ""), f"{name} empty", "minimal"))
            add(_case(_vary_position(base, position, value[:1] or "a"), f"{name} with one character", "minimal"))
            add(_case(_vary_position(base, position, (value[:1] or "a") * 6), f"{name} with one repeated character", "repeated"))
        elif isinstance(value, list):
            minimum = length_bounds[0] if length_bounds else 0
            numeric = bool(value) and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
            if minimum == 0:
                add(_case(_vary_position(base, position, []), f"{name} empty", "minimal"))
            if value and minimum <= 1:
                add(_case(_vary_position(base, position, value[:1]), f"{name} with one item", "minimal"))
            if value:
                add(_case(_vary_position(base, position, [value[0]] * max(minimum, 4)), f"{name} with repeated values", "repeated"))
            if numeric:
                item_bounds = bounds.get(f"{name}[i]") or bounds.get(name)
                if not item_bounds or item_bounds[0] < 0:
                    add(_case(_vary_position(base, position, [-abs(v) - 1 for v in value]), f"{name} with negative values", "negative"))
                if item_bounds:
                    add(_case(_vary_position(base, position, [item_bounds[1]] * max(minimum, 2)), f"{name} with its largest values", "boundary"))
                size = min(length_bounds[1] if length_bounds else 10000, MAX_LARGE_ITEMS)
                if size >= 100:
                    fill = list(range(1, size + 1))
                    add(_case(_vary_position(base, position, fill), f"{name} with {size:,} items: must finish in time", "large", compare="completes", needs=False))
                    notes.append("The large input test only checks your code finishes in time. Its answer is not checked.")
    notes.append("Tests marked \"needs expected output\" stay off until you enter the right answer yourself.")
    return tests, notes


def validate_tests(draft: ImportDraft, tests: list[TestCase]) -> None:
    """Refuse definitions that are invalid or unsafe to store. Details say which test to fix."""
    problems: list[dict[str, Any]] = []
    params = len(draft.parameters)
    enabled = 0
    for index, test in enumerate(tests):
        label = test.label or f"Test {index + 1}"
        if draft.mode == "function" and test.kind != "args":
            problems.append({"index": index, "label": label, "message": "This question reads a function call, so tests need arguments."})
        if draft.mode == "stdio" and test.kind != "stdio":
            problems.append({"index": index, "label": label, "message": "This question reads standard input, so tests need input text."})
        # A blank test that is switched off is harmless, so it does not block saving.
        blank_and_off = not test.enabled and not test.args
        if test.kind == "args" and params and test.args is not None and len(test.args) != params and not blank_and_off:
            problems.append({"index": index, "label": label, "message": f"Expected {params} argument(s), found {len(test.args)}."})
        if test.kind == "args" and test.args is None:
            problems.append({"index": index, "label": label, "message": "Arguments must be a JSON list."})
        try:
            size = len(json.dumps([test.args, test.stdin, test.expected]))
        except (TypeError, ValueError):
            problems.append({"index": index, "label": label, "message": "This test contains a value that cannot be stored."})
            continue
        if size > MAX_TEST_BYTES:
            problems.append({"index": index, "label": label, "message": "This test is too large (limit 256 KB)."})
        if test.enabled and test.needs_expected:
            problems.append({"index": index, "label": label, "message": "Enter the expected output before turning this test on."})
        if test.enabled:
            enabled += 1
    if problems:
        raise ApiError(422, "invalid_tests", "Some tests need attention before saving.", details=problems)
    _ = enabled
