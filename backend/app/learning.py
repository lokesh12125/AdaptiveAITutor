"""The Learn panel beside each problem, and search across topics and problems.

Each panel is built from the task text, the visible examples, the topic's notes and the guidance for its technique.
It never reads hidden tests or reference solutions, so it cannot give the answer away. Guidance is about how to think
about this kind of problem. The specific solution stays the learner's to find.
"""
from __future__ import annotations

import ast
import re
from functools import lru_cache
from typing import Any

import yaml
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .grading import display
from .models import Problem, Unit

DEFAULT_TECHNIQUE = "General problem solving"
HINT_STAGES = [
    {"name": "A question", "detail": "Something to think about, about your own code."},
    {"name": "A targeted hint", "detail": "Points at what to look at, using your code and the error."},
    {"name": "An outline", "detail": "The steps to take, in order, in words."},
    {"name": "A worked example", "detail": "The same idea on a different problem, never this one."},
]
LARGE_INPUT = re.compile(r"10\s*(?:\^|\*\*)\s*([4-9]|1\d)|\b\d{1,3}(?:,\d{3})+\b|\b\d{5,}\b")


@lru_cache(maxsize=1)
def techniques() -> dict[str, Any]:
    found: dict[str, Any] = {}
    for path in sorted((settings.content_path / "notes").glob("techniques_*.yaml")):
        found.update(yaml.safe_load(path.read_text()))
    steps_path = settings.content_path / "notes" / "approach_steps.yaml"
    steps = yaml.safe_load(steps_path.read_text()) if steps_path.exists() else {}
    for name, technique in found.items():
        approaches = technique.get("approaches") or []
        for index, approach in enumerate(approaches):
            if index == len(approaches) - 1:
                approach.setdefault("steps", technique.get("steps") or [])
                approach["main"] = True
            else:
                approach.setdefault("steps", (steps.get(name) or {}).get(approach["level"], []))
                approach["main"] = False
    return found


COST_WORDS = [
    ("O(1)", "a fixed amount of work, however large the input"), ("O(log", "the range halves at each step"), ("O(n log n)", "sorting, or halving work across every item"),
    ("O(n²)", "a pass over the input for every item"), ("O(n × m)", "every pair of positions from the two inputs"), ("O(r × c)", "every cell once"),
    ("O(2^n)", "trying every combination, which doubles with each item"), ("O(n!)", "trying every order"), ("O(V + E)", "each node and each edge once"),
    ("O(n)", "one pass over the input"), ("O(d)", "one step per digit"), ("O(k)", "one step per item kept"), ("O(h)", "one step per level of the tree"),
]


SPACE_WORDS = [
    ("O(1)", "only a few variables, however large the input"), ("O(log", "the depth of the halving"), ("O(n log n)", "copies made while splitting"),
    ("O(n²)", "a value for every pair"), ("O(n × m)", "a table with a cell for each pair of positions"), ("O(r × c)", "a table with a cell for each grid cell"),
    ("O(V + E)", "storing the graph"), ("O(V)", "one entry per node"), ("O(n)", "storing up to one thing per item"), ("O(d)", "one entry per digit"),
    ("O(k)", "keeping k items"), ("O(h)", "the depth of the recursion"), ("O(capacity)", "one entry per capacity value"), ("O(states)", "one stored answer per state"),
]


def cost_reason(cost: str, words: list[tuple[str, str]] | None = None) -> str | None:
    for start, reason in words or COST_WORDS:
        if cost.startswith(start):
            return reason
    return None


def _describe(value: Any) -> str:
    """A plain description of a visible value, such as a list of numbers."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True or False"
    if isinstance(value, int):
        return "a whole number"
    if isinstance(value, float):
        return "a decimal number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        if "$set" in value:
            return "a set of values"
        if "$tuple" in value:
            return "a tuple of values"
        return "a dictionary"
    if isinstance(value, (list, tuple)):
        if not value:
            return "a list"
        if all(isinstance(item, bool) for item in value):
            return "a list of True or False values"
        if all(isinstance(item, (int, float)) for item in value):
            return "a list of numbers"
        if all(isinstance(item, str) for item in value):
            return "a list of text values"
        if all(isinstance(item, (list, tuple)) for item in value):
            return "a list of lists"
        return "a list of values"
    return "a value"


def _facts_about(name: str, value: Any) -> str | None:
    """Things you can notice by looking at a visible input, which often point at the method."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (list, tuple)):
        items = list(value)
        if not items:
            return f"`{name}` is empty."
        notes = [f"`{name}` has {len(items)} item{'s' if len(items) != 1 else ''}"]
        if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in items) and len(items) > 1 and len(set(items)) > 1:
            if all(a < b for a, b in zip(items, items[1:], strict=False)):
                notes.append("in increasing order")
            elif items == sorted(items):
                notes.append("sorted from smallest to largest")
            elif items == sorted(items, reverse=True):
                notes.append("sorted from largest to smallest")
            if any(item < 0 for item in items):
                notes.append("including negative numbers")
        try:
            notes.append(("all the same value" if len(set(items)) == 1 and len(items) > 1 else "with repeated values") if len(set(items)) < len(items) else "with no repeats")
        except TypeError:
            pass
        return ", ".join(notes) + "."
    if isinstance(value, str):
        return f"`{name}` is {len(value)} character{'s' if len(value) != 1 else ''} long." if value else f"`{name}` is empty."
    if isinstance(value, (int, float)) and value <= 0:
        return f"`{name}` is {'zero' if value == 0 else 'negative'}, which is worth checking separately."
    return None


def _parameters(problem: Problem) -> list[str]:
    try:
        for node in ast.parse(problem.starter_code or "").body:
            if isinstance(node, ast.FunctionDef) and (not problem.function_name or node.name == problem.function_name):
                return [arg.arg for arg in node.args.args]
    except (SyntaxError, ValueError):
        pass
    return []


def _first_sentence(text: str) -> str:
    clean = (text or "").strip().split("\n\n")[0]
    parts = re.split(r"(?<=[.?!])\s+", clean)
    return (parts[0] if parts else clean)[:300]


def _input_and_output(problem: Problem, public: list[Any]) -> dict[str, Any]:
    first = public[0] if public else None
    params = _parameters(problem)
    inputs: list[dict[str, str]] = []
    facts: list[str] = []
    if problem.mode == "stdio":
        stdin = (first.payload or {}).get("stdin", "") if first else ""
        count = len(stdin.splitlines()) if stdin else 0
        lines = f"{count} line{'s' if count != 1 else ''} of input" if count else "input"
        return {"mode": "program", "inputs": [{"name": "input", "kind": lines}], "output": {"kind": "printed text", "example": first.expected if first and isinstance(first.expected, str) else None}, "facts": []}
    prelude = problem.prelude or ""
    arguments = (first.payload or {}).get("args") if first and first.kind == "args" else None
    for index, name in enumerate(params):
        if isinstance(arguments, list) and index < len(arguments):
            inputs.append({"name": name, "kind": _describe(arguments[index])})
            noted = _facts_about(name, arguments[index])
            if noted:
                facts.append(noted)
        elif "ListNode" in prelude and "TreeNode" not in prelude:
            inputs.append({"name": name, "kind": "the first node of a linked list"})
        elif "TreeNode" in prelude:
            inputs.append({"name": name, "kind": "the root of a binary tree"})
        else:
            inputs.append({"name": name, "kind": "a value"})
    expected = first.expected if first else None
    return {"mode": "function", "inputs": inputs, "output": {"kind": _describe(expected), "example": display(expected) if first and first.compare != "completes" else None}, "facts": facts}


def _constraints(problem: Problem) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for raw in re.split(r"\n+|(?<=\.)\s+", problem.constraints or ""):
        text = raw.strip(" -*")
        if not text:
            continue
        lowered = text.lower()
        if LARGE_INPUT.search(text):
            means = "Inputs can be large, so checking every pair is likely to be too slow."
        elif "sorted" in lowered:
            means = "The order is something you can use, for example to rule out items."
        elif "unique" in lowered or "distinct" in lowered:
            means = "You do not need to handle repeated values."
        elif "empty" in lowered:
            means = "Decide what the answer should be for empty input."
        elif "negative" in lowered:
            means = "Check that your method still works with negative values."
        else:
            means = "Keep this in mind when you test unusual inputs."
        found.append({"text": text, "means": means})
    limit = problem.per_test_seconds or 2
    found.append({"text": f"Each test has {limit:g} second{'s' if limit != 1 else ''} to finish.", "means": "A simple method is fine at first. Improve it if a test runs out of time."})
    return found


def _edge_cases(technique: dict[str, Any], inputs: list[dict[str, str]]) -> list[str]:
    cases = list(technique.get("edge_cases") or [])
    kinds = " ".join(item["kind"] for item in inputs)
    if "list" in kinds and not any("empty" in case.lower() for case in cases):
        cases.append("An empty list.")
    if "text" in kinds and not any("empty" in case.lower() for case in cases):
        cases.append("Empty text.")
    if "whole number" in kinds and not any("zero" in case.lower() or "negative" in case.lower() for case in cases):
        cases.append("Zero and negative numbers, if the task allows them.")
    return cases[:6]


def _lesson_section(guide: dict[str, Any], pattern: str | None) -> dict[str, str] | None:
    """The part of the lesson closest to this technique."""
    if not pattern:
        return None
    wanted = {word for word in re.findall(r"[a-z]+", pattern.lower()) if len(word) > 3}
    best, best_score = None, 0
    for section in guide.get("sections") or []:
        score = len(wanted & set(re.findall(r"[a-z]+", section.get("title", "").lower())))
        if score > best_score:
            best, best_score = section, score
    return {"id": best["id"], "title": best["title"]} if best else None


def _approaches(technique: dict[str, Any], known_pattern: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Each approach as a short piece of theory: why it works, the steps, and what it costs."""
    raw = technique.get("approaches") or []
    main_time = raw[-1]["time"] if raw else None
    written: list[dict[str, Any]] = []
    for index, approach in enumerate(raw):
        if approach.get("main"):
            when = (known_pattern or {}).get("when")
            intuition = [technique.get("idea") or approach["idea"]]
            if when:
                intuition.append(f"It fits when: {when[0].lower() + when[1:]}")
            if len(raw) > 1:
                intuition.append("This is the approach this problem is meant to practise.")
        elif index == 0:
            intuition = [approach["idea"], "This is the most direct way to a correct answer, so it makes a good first version to write and test."]
        else:
            intuition = [approach["idea"], "It does less work than the approach before it."]
        if not approach.get("main") and main_time and approach["time"] != main_time:
            reason = cost_reason(approach["time"])
            intuition.append(f"Its time grows with {reason}, so on large inputs the next approach is faster." if reason else "On large inputs, the next approach is faster.")
        written.append({
            "level": approach["level"], "idea": approach["idea"], "intuition": list(dict.fromkeys(intuition)), "steps": approach.get("steps") or [],
            "time": approach["time"], "space": approach["space"], "time_reason": cost_reason(approach["time"]), "space_reason": cost_reason(approach["space"], SPACE_WORDS), "main": bool(approach.get("main")),
        })
    return written


def build_problem_learning(db: Session, problem: Problem, solved: set[str], attempted: set[str]) -> dict[str, Any]:
    unit = db.get(Unit, problem.unit_id)
    guide = (unit.guide if unit else None) or {}
    library = techniques()
    name = problem.pattern if problem.pattern in library else DEFAULT_TECHNIQUE
    technique = library.get(name) or {}
    known_pattern = next((item for item in guide.get("patterns") or [] if item.get("name") == problem.pattern), None)
    public = [t for t in problem.tests if t.enabled and not t.needs_expected and t.visibility == "public"]
    shape = _input_and_output(problem, public)

    received = ", ".join(f"`{item['name']}` ({item['kind']})" for item in shape["inputs"])
    if shape["mode"] == "program":
        asking = f"Your program reads {shape['inputs'][0]['kind']} and prints the answer. It should print exactly that, with nothing extra."
    elif received:
        asking = f"You receive {received}. Your function should give back {shape['output']['kind']}."
    else:
        asking = f"Your function should give back {shape['output']['kind']}."

    worked = None
    if public:
        from .grading import describe_input

        first = public[0]
        expected = first.expected if first.kind == "stdio" else display(first.expected)
        worked = {"input": describe_input(first, problem.function_name), "expected": expected if first.compare != "completes" else None, "facts": shape.pop("facts", []), "steps": technique.get("steps") or []}

    # Other problems that use the same idea, easiest first, so a learner can build up to this one.
    siblings = db.scalars(select(Problem).where(Problem.unit_id == problem.unit_id, Problem.archived.is_(False), Problem.owner_id.is_(None), Problem.id != problem.id)).all()
    order = {"easy": 0, "medium": 1, "hard": 2}
    siblings = sorted(siblings, key=lambda p: (p.pattern != problem.pattern, order.get(p.difficulty or "", 3), p.title))
    related = [
        {"id": p.id, "title": p.title, "difficulty": p.difficulty, "pattern": p.pattern, "same_technique": p.pattern == problem.pattern, "status": "solved" if p.id in solved else ("in_progress" if p.id in attempted else "not_started")}
        for p in siblings[:5]
    ]
    prerequisite_rows = db.execute(select(Unit.id, Unit.title).where(Unit.id.in_(unit.prerequisites or []))).all() if unit else []

    return {
        "summary": _first_sentence(problem.description), "asking": asking, "shape": {"inputs": shape["inputs"], "output": shape["output"], "mode": shape["mode"]},
        "observations": technique.get("observations") or [], "constraints": _constraints(problem), "worked_example": worked,
        "technique": {"name": problem.pattern or DEFAULT_TECHNIQUE, "idea": technique.get("idea"), "when": (known_pattern or {}).get("when"), "how": (known_pattern or {}).get("how")},
        "approaches": _approaches(technique, known_pattern), "mistakes": technique.get("mistakes") or [], "edge_cases": _edge_cases(technique, shape["inputs"]),
        "concept": {
            "unit_id": problem.unit_id, "unit_title": unit.title if unit else problem.unit_id, "section": _lesson_section(guide, problem.pattern),
            "definitions": (guide.get("definitions") or [])[:4], "key_ideas": (guide.get("key_ideas") or [])[:3],
        },
        "prerequisites": {"topics": [{"id": uid, "title": title} for uid, title in prerequisite_rows], "know_first": guide.get("before_you_start") or []},
        "related": related, "hint_stages": HINT_STAGES,
        "revision": {"idea": technique.get("idea"), "summary": guide.get("summary")},
    }


# ---------------------------------------------------------------- search

def _matches(text: str | None, words: list[str]) -> bool:
    lowered = (text or "").lower()
    return all(word in lowered for word in words)


def search_everything(db: Session, query: str, owner_id: str) -> dict[str, list[dict[str, Any]]]:
    words = [word for word in re.findall(r"[a-z0-9_]+", query.lower()) if word][:6]
    if not words:
        return {"topics": [], "problems": []}
    topics: list[dict[str, Any]] = []
    for unit in db.scalars(select(Unit).order_by(Unit.order_index)).all():
        guide = unit.guide or {}
        match: dict[str, Any] | None = None
        if _matches(f"{unit.title} {unit.summary}", words):
            match = {"where": "Topic", "text": unit.summary, "section": None}
        if match is None:
            for section in guide.get("sections") or []:
                if _matches(section.get("title"), words):
                    match = {"where": "Lesson section", "text": section["title"], "section": section["id"]}
                    break
        if match is None:
            for entry in [*(guide.get("definitions") or []), *(guide.get("glossary") or [])]:
                if _matches(entry.get("term"), words):
                    match = {"where": "Glossary", "text": f"{entry['term']}: {entry['meaning']}", "section": "glossary"}
                    break
        if match is None:
            for pattern in guide.get("patterns") or []:
                if _matches(pattern.get("name"), words):
                    match = {"where": "Technique", "text": f"{pattern['name']}: {pattern.get('when', '')}", "section": "patterns"}
                    break
        if match is None:
            for section in guide.get("sections") or []:
                if _matches(section.get("body"), words):
                    match = {"where": "Lesson section", "text": section["title"], "section": section["id"]}
                    break
        if match:
            topics.append({"id": unit.id, "title": unit.title, **match})
    rows = db.scalars(select(Problem).where(Problem.archived.is_(False), or_(Problem.owner_id.is_(None), Problem.owner_id == owner_id)).order_by(Problem.title)).all()
    problems = []
    titles = {u.id: u.title for u in db.scalars(select(Unit)).all()}
    for problem in rows:
        if _matches(f"{problem.title} {problem.pattern or ''} {' '.join(problem.concepts or [])} {titles.get(problem.unit_id, '')}", words):
            problems.append({"id": problem.id, "title": problem.title, "difficulty": problem.difficulty, "pattern": problem.pattern, "unit_title": titles.get(problem.unit_id, ""), "unit_id": problem.unit_id})
    return {"topics": topics[:12], "problems": problems[:30]}
