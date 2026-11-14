"""What kind of case a test is, worked out from its input alone, so learners can see what the hidden tests cover.

Used when seeding the curriculum, and by scripts/problem_bank/extra_tests.py to choose generated tests that cover
different kinds of input rather than many near-copies of one. A label never reveals a test's input or answer.
"""
from __future__ import annotations

import ast
import re
from typing import Any

# Most telling first: a test gets the first label that applies.
ORDER = ["efficiency check", "large input", "empty input", "single item", "all the same", "reverse sorted", "sorted", "repeated values", "negative numbers", "zero", "one",
         "large number", "typical"]

PURPOSE = {
    "efficiency check": "A very large input. A correct but slow approach runs out of time here, so it shows whether the work grows sensibly with the input.",
    "large input": "A large input, to check your code finishes in time and does not depend on small sizes.",
    "empty input": "Nothing to work with, such as an empty list or text. Many first attempts forget this case.",
    "single item": "Just one item, the smallest non-empty case. Loops and boundaries often go wrong here.",
    "all the same": "Every value equal, which catches code that assumes values differ.",
    "reverse sorted": "Values in descending order, the opposite of what code often expects.",
    "sorted": "Values already in order, which can hide or expose mistakes in comparisons and boundaries.",
    "repeated values": "Some values appear more than once, which catches code that assumes they are all different.",
    "negative numbers": "Negative numbers, which catch code that assumes everything is positive.",
    "zero": "A zero, which catches mistakes with starting values, division and empty totals.",
    "one": "The value one, the smallest case for many counting and looping tasks.",
    "large number": "A big number, to check the method still works and finishes when values are large.",
    "typical": "An ordinary input of a normal size, like the examples.",
}
LARGE, EFFICIENCY = 300, 5000


def _values_from_expr(expr: str) -> list[Any]:
    """Literal arguments inside an expression test, such as the list in `total(build_list([1, 2]))`."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return []
    found: list[Any] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for arg in node.args:
                if isinstance(arg, (ast.List, ast.Tuple, ast.Constant, ast.Dict, ast.UnaryOp)):
                    try:
                        found.append(ast.literal_eval(arg))
                    except (ValueError, SyntaxError):
                        continue
    return found


def _values_from_stdin(stdin: str) -> list[Any]:
    lines = stdin.rstrip("\n").split("\n") if stdin.strip() else []
    if not lines:
        return [""]
    numbers = [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", stdin)]
    tokens = stdin.split()
    return [tokens, *numbers] if len(tokens) > 1 else [tokens[0] if tokens else "", *numbers]


def _labels_for(value: Any, labels: set[str]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        if value == 0:
            labels.add("zero")
        elif value < 0:
            labels.add("negative numbers")
        elif value == 1:
            labels.add("one")
        if abs(value) >= 1000:
            labels.add("large number")
        return
    if isinstance(value, (str, list, tuple, dict, set)):
        size = len(value)
        if size >= EFFICIENCY:
            labels.add("efficiency check")
        elif size >= LARGE:
            labels.add("large input")
        if size == 0:
            labels.add("empty input")
        elif size == 1 and not isinstance(value, str):
            labels.add("single item")
        elif isinstance(value, str) and size == 1:
            labels.add("single item")
    if isinstance(value, (list, tuple)) and value:
        flat = [v for v in value if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(flat) == len(value) and len(flat) >= 2:
            if len(set(flat)) == 1:
                labels.add("all the same")
            elif len(flat) >= 3 and all(a <= b for a, b in zip(flat, flat[1:])):
                labels.add("sorted")
            elif len(flat) >= 3 and all(a >= b for a, b in zip(flat, flat[1:])):
                labels.add("reverse sorted")
            if len(set(flat)) < len(flat):
                labels.add("repeated values")
        for item in value[:EFFICIENCY]:
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                if item < 0:
                    labels.add("negative numbers")
                elif item == 0:
                    labels.add("zero")
            elif isinstance(item, (list, tuple)):
                _labels_for(item, labels)
                labels.discard("empty input") if item == [] and value else None


def categorise(test: dict[str, Any]) -> list[str]:
    """Every label that applies, most telling first. Accepts a stored test (`args`, `stdin` or `expr`)."""
    if "args" in test and test.get("args") is not None:
        values = list(test["args"])
    elif "stdin" in test and test.get("stdin") is not None:
        values = _values_from_stdin(str(test["stdin"]))
    elif test.get("expr"):
        values = _values_from_expr(str(test["expr"]))
    else:
        values = []
    labels: set[str] = set()
    for value in values:
        _labels_for(value, labels)
    return [label for label in ORDER if label in labels] or ["typical"]


def primary(test: dict[str, Any]) -> str:
    return categorise(test)[0]
