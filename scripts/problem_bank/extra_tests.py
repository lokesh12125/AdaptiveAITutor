#!/usr/bin/env python3
"""Add more hidden tests to each problem, worked out from its own examples and reference solution.

Run from the repository root:  backend/.venv/bin/python scripts/problem_bank/extra_tests.py

For each problem whose tests call a function with plain values, this reads every existing test and notes what all
of them have in common: types, value ranges, lengths, and properties such as sorted, distinct or non-empty, plus how
arguments relate (an index that is always within a list, for example). New inputs keep all of those, so they stay
within what the task allows. The reference solution gives each answer.

A correct solution that relies on a rule the examples do not show could still fail a generated input, so problems
whose task mentions such rules (guarantees, several valid answers, ties) are skipped, as is a list checked by hand.
Writes content/problems/extra_tests.yaml, which the seed adds as hidden tests.
"""
from __future__ import annotations

import copy
import json
import random
import re
import signal
import string
import sys
import time
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from build import encode, run_program  # noqa: E402
from custom_inputs import EFFICIENCY, GENERATORS, HANDWRITTEN, LARGE, SCRIPTS  # noqa: E402

sys.path.insert(0, str(ROOT / "backend"))
from app.test_categories import ORDER, categorise  # noqa: E402

TARGET_TOTAL = 32  # tests per problem, counting the ones already written, before any large-input tests
CANDIDATES = 3000  # attempts at a valid new input
POOL = 400  # valid inputs to choose from, so the chosen ones can cover different kinds of case
RISKY = re.compile(
    r"guarantee|assume|exactly one|any order|any one|any of them|one of them|if there are several|if several|if more than one|"
    r"\btie|\bties\b|at least one|always exists|valid|well-formed|balanced|you may|may return|either|permutation|anagram|"
    r"\bindices\b|\bindex of\b|positions? of|majority|most (common|frequent)|kth|k-th|median|mode\b|unique answer|"
    r"\bdistinct\b|non-?overlapping|interval|matrix|grid|graph|tree|node|edge|reachable",
    re.IGNORECASE,
)
# Checked by hand: their inputs follow rules the examples alone do not show.
SKIP = {
    "roman-to-integer", "integer-to-roman", "valid-parentheses", "evaluate-expression", "decode-string", "is-valid-date", "next-permutation",
    "binary-to-decimal", "hex-to-decimal", "parse-time", "simplify-file-path", "longest-balanced-brackets", "min-remove-to-balance",
    # Found when reviewing the generated inputs: structured text, token lists, or rules such as "always reachable".
    "basic-calculator-plus-minus", "decode-repeat-string", "evaluate-rpn", "word-ladder-steps", "recent-counter-queue-processor", "normalize-module-name",
    "point-quadrant", "capitalise-each-word", "pair-with-target-sum", "min-jumps-to-end", "queue-simulation-order", "word-pattern-match",
}


class Timeout(Exception):
    pass


def _alarm(*_):
    raise Timeout


signal.signal(signal.SIGALRM, _alarm)


def kind_of(value: Any) -> str | None:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        if not value:
            return "list:?"
        inner = {kind_of(item) for item in value}
        if len(inner) == 1 and next(iter(inner)) in ("int", "str", "bool", "float"):
            return f"list:{next(iter(inner))}"
        return None
    return None


def merge_kind(kinds: set[str]) -> str | None:
    concrete = {k for k in kinds if k != "list:?"}
    if len(concrete) == 1:
        return next(iter(concrete))
    if not concrete and kinds == {"list:?"}:
        return None
    if concrete == {"int", "float"}:
        return "float"
    return None


def profile(values: list[Any], kind: str) -> dict[str, Any]:
    info: dict[str, Any] = {"kind": kind}
    if kind in ("int", "float"):
        info["lo"], info["hi"] = min(values), max(values)
    elif kind == "str":
        info["chars"] = sorted(set("".join(values))) or list(string.ascii_lowercase)
        info["min_len"], info["max_len"] = min(map(len, values)), max(map(len, values))
        info["palindrome"] = all(v == v[::-1] for v in values)
    elif kind.startswith("list:"):
        lengths = [len(v) for v in values]
        info["min_len"], info["max_len"] = min(lengths), max(lengths)
        items = [x for v in values for x in v]
        inner = kind.split(":")[1]
        if inner in ("int", "float") and items:
            info["lo"], info["hi"] = min(items), max(items)
        if inner == "str" and items:
            info["chars"] = sorted(set("".join(items))) or list(string.ascii_lowercase)
            info["item_min"], info["item_max"] = min(map(len, items)), max(map(len, items))
        info["sorted"] = all(v == sorted(v) for v in values) and any(len(v) > 1 for v in values)
        info["sorted_desc"] = all(v == sorted(v, reverse=True) for v in values) and any(len(v) > 1 for v in values) and not info["sorted"]
        info["distinct"] = all(len(set(map(json.dumps, v))) == len(v) for v in values)
    return info


def relations(arg_lists: list[list[Any]], kinds: list[str]) -> list[tuple[str, int, int]]:
    """How an int argument relates to a sequence argument, if every test agrees."""
    found = []
    for i, ki in enumerate(kinds):
        if ki != "int":
            continue
        for j, kj in enumerate(kinds):
            if j == i or not (kj == "str" or kj.startswith("list:")):
                continue
            pairs = [(args[i], len(args[j])) for args in arg_lists]
            if all(0 <= a < n for a, n in pairs):
                found.append(("index", i, j))
            elif all(1 <= a <= n for a, n in pairs):
                found.append(("count1", i, j))
            elif all(0 <= a <= n for a, n in pairs):
                found.append(("count0", i, j))
            if kj.startswith("list:") and all(args[i] in args[j] for args in arg_lists):
                found.append(("member", i, j))
            if all(a >= n for a, n in pairs) and not any(r[1] == i and r[2] == j for r in found):
                found.append(("at_least_len", i, j))
    for i, ki in enumerate(kinds):
        for j in range(i + 1, len(kinds)):
            kj = kinds[j]
            sequences = (ki == "str" or ki.startswith("list:")) and (kj == "str" or kj.startswith("list:"))
            if sequences and all(len(args[i]) == len(args[j]) for args in arg_lists):
                found.append(("same_len", i, j))
            if ki in ("int", "float") and kj in ("int", "float") and all(args[i] <= args[j] for args in arg_lists):
                found.append(("ordered", i, j))
    return found


def make_number(info: dict[str, Any], rng: random.Random) -> Any:
    lo, hi = info["lo"], info["hi"]
    if info["kind"] == "float":
        return round(rng.uniform(lo, hi), 2) if hi > lo else lo
    return rng.randint(lo, hi)


def make_value(info: dict[str, Any], rng: random.Random, forced: int | None = None) -> Any:
    kind = info["kind"]
    if kind in ("int", "float"):
        return make_number(info, rng)
    if kind == "bool":
        return rng.random() < 0.5
    if kind == "str":
        # If every example has the same length, the length is probably part of the task, so keep it.
        length = info["min_len"] if info["min_len"] == info["max_len"] else rng.randint(info["min_len"], max(info["min_len"], min(info["max_len"] + 4, 16)))
        length = forced if forced is not None else length
        text = "".join(rng.choice(info["chars"]) for _ in range(length))
        if info.get("palindrome"):
            half = text[: (length + 1) // 2]
            text = half + half[: length // 2][::-1]
        return text
    inner = kind.split(":")[1]
    length = info["min_len"] if info["min_len"] == info["max_len"] else rng.randint(info["min_len"], max(info["min_len"], min(info["max_len"] + 4, 12)))
    length = forced if forced is not None else length
    items: list[Any] = []
    attempts = 0
    while len(items) < length and attempts < 200:
        attempts += 1
        if inner in ("int", "float"):
            item = make_number({"kind": inner, "lo": info["lo"], "hi": info["hi"]}, rng)
        elif inner == "str":
            size = rng.randint(info.get("item_min", 1), max(info.get("item_min", 1), min(info.get("item_max", 5) + 2, 10)))
            item = "".join(rng.choice(info["chars"]) for _ in range(size))
        else:
            item = rng.random() < 0.5
        if info.get("distinct") and item in items:
            continue
        items.append(item)
    if info.get("sorted"):
        items.sort()
    elif info.get("sorted_desc"):
        items.sort(reverse=True)
    return items


def generate(args_lists: list[list[Any]], rng: random.Random) -> list[Any] | None:
    count = len(args_lists[0])
    if any(len(a) != count for a in args_lists):
        return None
    kinds = []
    for position in range(count):
        kind = merge_kind({kind_of(a[position]) for a in args_lists})
        if kind is None:
            return None
        kinds.append(kind)
    infos = [profile([a[p] for a in args_lists], kinds[p]) for p in range(count)]
    rels = relations(args_lists, kinds)
    candidate = [make_value(info, rng) for info in infos]
    for name, i, j in rels:
        if name == "same_len":
            candidate[j] = make_value(infos[j], rng, forced=len(candidate[i]))
        elif name == "ordered" and candidate[i] > candidate[j]:
            candidate[i], candidate[j] = candidate[j], candidate[i]
    for name, i, j in rels:
        if name in ("same_len", "ordered"):
            continue
        size = len(candidate[j])
        if name == "member":
            if not candidate[j]:
                return None
            candidate[i] = rng.choice(candidate[j])
        elif name == "index":
            if size == 0:
                return None
            candidate[i] = rng.randrange(size)
        elif name == "count1":
            if size == 0:
                return None
            candidate[i] = rng.randint(1, size)
        elif name == "count0":
            candidate[i] = rng.randint(0, size)
        elif name == "at_least_len":
            candidate[i] = rng.randint(size, max(size, infos[i]["hi"]))
    return candidate


def call(code: str, prelude: str | None, name: str, args: list[Any], seconds: float = 0.5) -> Any:
    namespace: dict[str, Any] = {}
    if prelude:
        exec(prelude, namespace)
    exec(code, namespace)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return namespace[name](*copy.deepcopy(args))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def same_shape(value: Any, examples: list[Any]) -> bool:
    shapes = {type(e).__name__ for e in examples}
    return type(encode(value)).__name__ in shapes or (isinstance(encode(value), (int, float)) and shapes <= {"int", "float"})


def _size(test: dict[str, Any]) -> int:
    if "args" in test:
        return sum(len(a) if isinstance(a, (str, list, dict)) else 1 for a in test["args"])
    return len(str(test.get("stdin") or test.get("expr") or ""))


def _answer(test: dict[str, Any]) -> str:
    return json.dumps(test.get("expected", test.get("expected_stdout")), sort_keys=True, default=str)


def _features(test: dict[str, Any]) -> set[str]:
    """Small facts about an input, so the chosen tests differ in more than their exact values."""
    found: set[str] = set()
    values = test["args"] if "args" in test else [test.get("stdin") or test.get("expr") or ""]
    for position, value in enumerate(values):
        tag = f"{position}:"
        if isinstance(value, bool) or value is None:
            found.add(f"{tag}{value}")
        elif isinstance(value, (int, float)):
            number = int(value) if float(value).is_integer() else None
            found.add(f"{tag}sign{(value > 0) - (value < 0)}")
            if number is not None:
                found |= {f"{tag}even{number % 2 == 0}", f"{tag}by3{number % 3 == 0}", f"{tag}by5{number % 5 == 0}", f"{tag}digits{len(str(abs(number)))}"}
            else:
                found.add(f"{tag}fraction")
        elif isinstance(value, str):
            found |= {f"{tag}len{min(len(value), 12) // 3}", f"{tag}upper{any(c.isupper() for c in value)}", f"{tag}space{' ' in value}", f"{tag}digit{any(c.isdigit() for c in value)}"}
        elif isinstance(value, (list, tuple, dict)):
            found.add(f"{tag}len{min(len(value), 40) // 4}")
            if isinstance(value, list) and value and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
                found |= {f"{tag}sorted{value == sorted(value)}", f"{tag}distinct{len(set(value)) == len(value)}", f"{tag}neg{min(value) < 0}"}
    return found


def choose(pool: list[dict[str, Any]], existing: list[dict[str, Any]], wanted: int) -> list[dict[str, Any]]:
    """Pick tests that add coverage rather than near-copies.

    First, one test for each kind of case the written tests lack. Then, repeatedly, the candidate that adds the most:
    a new answer, a rarely chosen kind of case, input features not yet covered, and a new size, with a penalty for
    repeating an answer, and a larger one for repeating both the kind of case and the answer.
    """
    if wanted <= 0 or not pool:
        return []
    labels = [categorise(t) for t in pool]
    answers_of = [_answer(t) for t in pool]
    features_of = [_features(t) for t in pool]
    covered = {categorise(t)[0] for t in existing}
    answer_count: dict[str, int] = {}
    pair_count: dict[tuple[str, str], int] = {}
    per_label: dict[str, int] = {}
    features: set[str] = set()
    sizes: set[int] = set()
    for test in existing:
        answer = _answer(test)
        answer_count[answer] = answer_count.get(answer, 0) + 1
        pair = (categorise(test)[0], answer)
        pair_count[pair] = pair_count.get(pair, 0) + 1
        features |= _features(test)
        sizes.add(min(_size(test), 50) // 5)
    chosen: list[int] = []

    def take(index: int) -> None:
        chosen.append(index)
        label, answer = labels[index][0], answers_of[index]
        per_label[label] = per_label.get(label, 0) + 1
        answer_count[answer] = answer_count.get(answer, 0) + 1
        pair_count[(label, answer)] = pair_count.get((label, answer), 0) + 1
        features.update(features_of[index])
        sizes.add(min(_size(pool[index]), 50) // 5)

    for label in ORDER:
        if len(chosen) >= wanted:
            break
        if label in covered or label == "typical":
            continue
        index = next((i for i, found in enumerate(labels) if label in found and i not in chosen), None)
        if index is not None:
            take(index)

    def score(i: int) -> tuple[float, int]:
        answer, label = answers_of[i], labels[i][0]
        repeats = answer_count.get(answer, 0)
        value = (3.0 if repeats == 0 else -1.5 * repeats) - 2.0 * pair_count.get((label, answer), 0)
        value += 2 / (1 + per_label.get(label, 0)) + 0.5 * len(features_of[i] - features)
        value += 1 if min(_size(pool[i]), 50) // 5 not in sizes else 0
        return (value, -i)

    while len(chosen) < wanted and len(chosen) < len(pool):
        take(max((i for i in range(len(pool)) if i not in chosen), key=score))
    return [pool[i] for i in sorted(chosen)]


def large_tests(slug: str, problem: dict[str, Any], code: str, call_template: str | None) -> list[dict[str, Any]]:
    """One large input, and a very large one when the task asks for an efficient approach. Answers stay short."""
    found: list[dict[str, Any]] = []
    name = problem.get("function_name") or (re.search(r"def (\w+)\(", problem["starter_code"]).group(1) if "def " in problem.get("starter_code", "") else None)
    for maker in (LARGE.get(slug), EFFICIENCY.get(slug)):
        if maker is None or not name:
            continue
        args = maker(random.Random(f"codepath-large:{slug}:{len(found)}"))
        try:
            started = time.perf_counter()
            result = call(code, problem.get("prelude"), name, args, seconds=2.0)
            elapsed = time.perf_counter() - started
        except Exception as error:  # noqa: BLE001 - reported, so a broken generator gets fixed
            print(f"LARGE FAILED {slug}: {error!r}")
            continue
        answer = encode(result)
        if elapsed > 0.5 or len(json.dumps(answer, default=str)) > 2000:
            print(f"LARGE SKIPPED {slug}: {elapsed:.2f}s, answer of {len(json.dumps(answer, default=str))} characters")
            continue
        found.append({"args": args, "expected": answer})
    return found


def custom_tests(problem: dict[str, Any], code: str, call: str | None, wanted: int) -> list[dict[str, Any]]:
    """Tests for a problem with its own input generator, or hand-written expressions. Answers come from the reference."""
    slug = problem["slug"]
    prelude = problem.get("prelude")
    tests = problem["tests"]
    seen = {json.dumps({k: t.get(k) for k in ("args", "stdin", "setup", "expr")}, sort_keys=True, default=str) for t in tests}
    found: list[dict[str, Any]] = []

    def evaluate(setup: str, expr: str) -> Any:
        namespace: dict[str, Any] = {}
        if prelude:
            exec(prelude, namespace)
        exec(code, namespace)
        signal.setitimer(signal.ITIMER_REAL, 1.0)
        try:
            if setup:
                exec(setup, namespace)
            return eval(expr, namespace)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    if slug in HANDWRITTEN:
        for setup, expr in HANDWRITTEN[slug]:
            key = json.dumps({"args": None, "stdin": None, "setup": setup, "expr": expr}, sort_keys=True)
            if key in seen or len(found) >= wanted:
                continue
            seen.add(key)
            try:
                value = evaluate(setup, expr)
            except Exception as error:  # noqa: BLE001 - reported, so a broken hand-written test gets fixed
                print(f"HANDWRITTEN FAILED {slug}: {expr!r}: {error!r}")
                continue
            found.append({"setup": setup, "expr": expr, "expected": encode(value)})
        if slug not in SCRIPTS:
            return found
    if slug in SCRIPTS:
        # Scripts of valid calls on a class or generator. Hand-written ones stay first, and the rest add coverage.
        written, pool = list(found), []
        rng = random.Random(f"codepath-script:{slug}")
        for _ in range(CANDIDATES):
            if len(pool) >= POOL:
                break
            setup, expr = SCRIPTS[slug](rng)
            key = json.dumps({"args": None, "stdin": None, "setup": setup, "expr": expr}, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            try:
                pool.append({"setup": setup, "expr": expr, "expected": encode(evaluate(setup, expr))})
            except Exception:  # noqa: BLE001 - a script the reference cannot run is not used
                continue
        return written + choose(pool, tests + written, wanted - len(written))
    rng = random.Random(f"codepath-custom:{slug}")
    name = problem.get("function_name") or (re.search(r"def (\w+)\(", problem["starter_code"]).group(1) if "def " in problem["starter_code"] else None)
    for _ in range(CANDIDATES):
        if len(found) >= POOL:
            break
        raw = GENERATORS[slug](rng)
        try:
            if isinstance(raw, str):
                key = json.dumps({"args": None, "stdin": raw, "setup": None, "expr": None}, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                found.append({"stdin": raw, "expected_stdout": run_program(code, raw)})
            elif call:
                expr = call.format(*[repr(a) for a in raw])
                key = json.dumps({"args": None, "stdin": None, "setup": "", "expr": expr}, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                found.append({"expr": expr, "expected": encode(evaluate("", expr))})
            else:
                key = json.dumps({"args": raw, "stdin": None, "setup": None, "expr": None}, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                if any(isinstance(a, (set, tuple)) for a in raw) or (raw and isinstance(raw[0], dict) and any(not isinstance(k, str) for k in raw[0])):
                    continue  # the tests carry arguments as JSON, which has no sets or tuples
                found.append({"args": raw, "expected": encode(call_function(code, prelude, name, raw))})
        except Exception:  # noqa: BLE001 - an input the reference cannot handle is not used
            continue
    return choose(found, tests, wanted)


def call_function(code: str, prelude: str | None, name: str, args: list[Any]) -> Any:
    return call(code, prelude, name, args)


def main() -> int:
    problems = json.loads((ROOT / "content/problems/legacy.json").read_text()) + yaml.safe_load((ROOT / "content/problems/authored.yaml").read_text()) + yaml.safe_load((ROOT / "content/problems/bank.yaml").read_text())
    solutions: dict[str, str] = {}
    for name in ("legacy", "authored", "bank"):
        solutions.update(yaml.safe_load((ROOT / f"content/solutions/{name}.yaml").read_text()))
    import dsl
    for module in ("foundations", "core_python", "algorithms", "structures", "advanced", "more_foundations", "more_algorithms", "more_structures", "more_advanced"):
        __import__(module)
    calls = {p["slug"]: p.get("call") for p in dsl.PROBLEMS}
    output: dict[str, list[dict[str, Any]]] = {}
    skipped: dict[str, str] = {}
    for problem in problems:
        slug = problem["slug"]
        tests = problem["tests"]
        if slug in GENERATORS or slug in HANDWRITTEN or slug in SCRIPTS:
            code = solutions.get(slug)
            if code:
                made = custom_tests(problem, code, calls.get(slug), max(0, TARGET_TOTAL - len(tests))) + large_tests(slug, problem, code, calls.get(slug))
                if made:
                    output[slug] = made
                    continue
            skipped[slug] = "no reference solution, or no custom inputs worked"
            continue
        if problem.get("mode", "function") != "function" or not problem.get("function_name") and "def " not in problem.get("starter_code", ""):
            skipped[slug] = "not a function problem"
            continue
        if any("args" not in t or t.get("compare", "exact") != "exact" for t in tests):
            skipped[slug] = "tests are not plain function calls"
            continue
        if slug in SKIP or RISKY.search(f"{problem['title']} {problem['description']}"):
            skipped[slug] = "the task has rules the examples may not show"
            continue
        code = solutions.get(slug)
        if not code:
            skipped[slug] = "no reference solution"
            continue
        name = problem.get("function_name") or re.search(r"def (\w+)\(", problem["starter_code"]).group(1)
        args_lists = [t["args"] for t in tests]
        expected = [t["expected"] for t in tests]
        if any(e is None for e in expected) or not args_lists or not args_lists[0]:
            skipped[slug] = "no arguments, or no stored answers"
            continue
        rng = random.Random(f"codepath:{slug}")
        seen = {json.dumps(a, sort_keys=True) for a in args_lists}
        found: list[dict[str, Any]] = []
        wanted = max(0, TARGET_TOTAL - len(tests))
        for _ in range(CANDIDATES):
            if len(found) >= POOL:
                break
            candidate = generate(args_lists, rng)
            if candidate is None:
                break
            key = json.dumps(candidate, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            try:
                result = call(code, problem.get("prelude"), name, candidate)
            except Exception:  # noqa: BLE001 - an input the reference cannot handle is simply not used
                continue
            if result is None or not same_shape(result, expected):
                continue
            found.append({"args": candidate, "expected": encode(result)})
        found = choose(found, tests, wanted) + large_tests(slug, problem, code, None)
        if found:
            output[slug] = found
        else:
            skipped.setdefault(slug, "no suitable inputs found")
    header = "# Generated by scripts/problem_bank/extra_tests.py from each problem's own examples. Answers come from the reference solution.\n"
    (ROOT / "content/problems/extra_tests.yaml").write_text(header + yaml.safe_dump(output, sort_keys=True, allow_unicode=True, width=200))
    added = sum(len(v) for v in output.values())
    print(f"Added {added} tests to {len(output)} problems. Skipped {len(skipped)}.")
    reasons: dict[str, int] = {}
    for reason in skipped.values():
        reasons[reason] = reasons.get(reason, 0) + 1
    print(reasons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
