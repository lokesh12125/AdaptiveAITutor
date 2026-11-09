"""Deterministic parsing of pasted problem statements. Nothing is invented: each field comes from the
text, or it is reported as missing so the learner can fill it in during review."""
from __future__ import annotations

import ast
import keyword
import re
from typing import Any

from ..schemas import ImportDraft, ImportExample

SECTION_NAMES = {
    "constraints": r"constraints?|limits?",
    "input_format": r"input(?:\s+format|\s+description)?|inputs?",
    "output_format": r"output(?:\s+format|\s+description)?|outputs?|returns?",
    "examples": r"examples?(?:\s*\d+)?|samples?|sample\s+cases?|test\s+cases?",
    "description": r"(?:problem\s+)?(?:description|statement)|problem|task",
    "notes": r"notes?|explanation|follow[\s-]*up|hints?",
}
HEADING = re.compile(r"^\s*(?:#{1,4}\s*)?\**\s*(" + "|".join(SECTION_NAMES.values()) + r")\s*\**\s*:?\s*$", re.I)
DIFFICULTY_LINE = re.compile(r"^\s*(?:difficulty\s*:?\s*)?(easy|medium|hard)\s*$", re.I)
LEADING_NUMBER = re.compile(r"^\s*\d+\s*[.)\-:]\s*")
UNIT_KEYWORDS = [
    ("dynamic-programming", ["dynamic programming", "memoization", "subsequence", "knapsack", " dp "]),
    ("graphs", ["graph", "bfs", "dfs", "breadth-first", "depth-first", "topological", "shortest path", "island"]),
    ("trees", ["binary tree", "bst", "tree", "traversal"]),
    ("linked-lists", ["linked list", "listnode"]),
    ("stacks-queues", ["stack", "queue", "parentheses", "monotonic"]),
    ("hashing", ["hash", "dictionary", "anagram", "frequency"]),
    ("arrays-two-pointers", ["two pointer", "two-pointer", "sliding window", "subarray", "array"]),
    ("searching-sorting", ["binary search", "sort", "search"]),
    ("recursion", ["recursion", "recursive", "backtrack"]),
    ("strings", ["string", "substring", "palindrome", "character"]),
    ("lists-dicts", ["list"]),
    ("loops", ["loop", "iterate"]),
]
TAG_TO_UNIT = {
    "dp": "dynamic-programming", "dynamic programming": "dynamic-programming", "graphs": "graphs", "dfs and similar": "graphs", "shortest paths": "graphs",
    "trees": "trees", "data structures": "stacks-queues", "two pointers": "arrays-two-pointers", "hashing": "hashing", "binary search": "searching-sorting",
    "sortings": "searching-sorting", "strings": "strings", "greedy": "arrays-two-pointers", "math": "loops", "implementation": "loops", "brute force": "loops", "number theory": "loops",
}


def literal(text: str) -> tuple[bool, Any]:
    """Read a value written in Python, JSON or common judge notation."""
    cleaned = text.strip().rstrip(".,;")
    if not cleaned:
        return False, None
    swaps = {"true": "True", "false": "False", "null": "None", "nil": "None"}
    candidate = re.sub(r"\b(true|false|null|nil)\b", lambda m: swaps[m.group(1)], cleaned)
    try:
        return True, ast.literal_eval(candidate)
    except (ValueError, SyntaxError):
        pass
    if re.fullmatch(r"[A-Za-z][\w\- ]*", cleaned) and len(cleaned) < 60:
        return True, cleaned  # an unquoted word, as in `Output: YES`
    return False, None


def split_top_level(text: str) -> list[str]:
    parts, depth, quote, current = [], 0, None, []
    for ch in text:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


NAMED_ARG = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", re.S)


def parse_call_input(text: str) -> tuple[list[str], list[Any] | None]:
    names: list[str] = []
    values: list[Any] = []
    for part in split_top_level(text):
        match = NAMED_ARG.match(part)
        raw = match.group(2) if match else part
        ok, value = literal(raw)
        if not ok:
            return [], None
        if match:
            names.append(match.group(1))
        values.append(value)
    if not values:
        return [], None
    return names if len(names) == len(values) else [], values


INLINE_EXAMPLE = re.compile(
    r"(?:^|\n)\s*\**\s*input\s*\**\s*[:：]\s*\**\s*(?P<input>.+?)\s*\n\s*\**\s*output\s*\**\s*[:：]\s*\**\s*(?P<output>.+?)\s*(?=\n|$)",
    re.I | re.S,
)
INLINE_ONE_LINE = re.compile(r"input\s*[:：]\s*(?P<input>[^\n]+?)\s+output\s*[:：]\s*(?P<output>[^\n]+)", re.I)
CALL_ARROW = re.compile(r"`?([A-Za-z_][A-Za-z0-9_]*)\(([^`\n]*)\)`?\s*(?:->|→|=>|==|returns?|should\s+return|is|gives?)\s*`?([^`\n]+?)`?\s*\.?\s*$", re.I | re.M)
SAMPLE_BLOCK = re.compile(
    r"sample\s+input\s*(?:#?\s*\d+)?\s*:?\s*\n(?P<input>.*?)\n\s*sample\s+output\s*(?:#?\s*\d+)?\s*:?\s*\n(?P<output>.*?)(?=\n\s*(?:sample\s+input|explanation|note|$)|\Z)",
    re.I | re.S,
)
DEF_NAME = re.compile(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
FENCE_LINES = re.compile(r"^```.*$", re.M)


def _snake(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    name = "_".join(words[:5]) or "solve"
    if name[0].isdigit():
        name = "solve_" + name
    return name if not keyword.iskeyword(name) else name + "_fn"


def _extract_sections(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    sections: dict[str, list[str]] = {}
    current = "preamble"
    sections[current] = []
    for line in lines:
        match = HEADING.match(line)
        if match:
            word = match.group(1).lower()
            for name, pattern in SECTION_NAMES.items():
                if re.fullmatch(pattern, word, re.I):
                    current = name
                    sections.setdefault(current, [])
                    break
            continue
        sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}, sections["preamble"]


def suggest_unit(text: str, tags: list[str]) -> str | None:
    for tag in tags:
        if tag.lower() in TAG_TO_UNIT:
            return TAG_TO_UNIT[tag.lower()]
    lowered = f" {text.lower()} "
    for unit, words in UNIT_KEYWORDS:
        if any(word in lowered for word in words):
            return unit
    return None


def parse_problem_text(text: str) -> ImportDraft:
    text = text.replace("\r\n", "\n").replace(" ", " ").strip()
    lines = text.split("\n")
    warnings: list[str] = []

    difficulty = None
    title = ""
    remaining = list(lines)
    for index, line in enumerate(lines[:6]):
        stripped = line.strip().lstrip("#").strip().strip("*").strip()
        if not stripped:
            continue
        if DIFFICULTY_LINE.match(stripped):
            difficulty = DIFFICULTY_LINE.match(stripped).group(1).lower()
            remaining[index] = ""
            continue
        if not title and len(stripped) <= 100 and not HEADING.match(line) and not stripped.endswith((".", ":", "?")):
            title = LEADING_NUMBER.sub("", stripped)
            remaining[index] = ""
    if difficulty is None:
        for index, line in enumerate(remaining):
            if DIFFICULTY_LINE.match(line):
                difficulty = DIFFICULTY_LINE.match(line).group(1).lower()
                remaining[index] = ""
                break

    sections, _ = _extract_sections(remaining)
    full = "\n".join(remaining)

    examples: list[ImportExample] = []
    mode = "function"
    parameters: list[str] = []
    function_name = None

    definition = DEF_NAME.search(full)
    if definition:
        function_name = definition.group(1)
        parameters = [p.split(":")[0].split("=")[0].strip() for p in definition.group(2).split(",") if p.strip() and p.strip() != "self"]

    samples = list(SAMPLE_BLOCK.finditer(FENCE_LINES.sub("", full)))
    inline = list(INLINE_EXAMPLE.finditer(full))
    if samples:
        mode = "stdio"
        for match in samples:
            stdin, stdout = match.group("input").strip(), match.group("output").strip()
            examples.append(ImportExample(input_text=stdin, output_text=stdout, stdin=stdin + "\n", expected_stdout=stdout + "\n", parsed=True))
    elif inline:
        multi_line_input = False
        for match in inline:
            input_text = match.group("input").strip().strip("`")
            output_text = match.group("output").strip().strip("`")
            names, values = parse_call_input(input_text)
            ok, expected = literal(output_text)
            if "\n" in input_text:
                multi_line_input = True
            if values is not None and ok and "\n" not in input_text:
                if names and not parameters:
                    parameters = names
                examples.append(ImportExample(input_text=input_text, output_text=output_text, args=values, expected=expected, parsed=True))
            else:
                examples.append(ImportExample(input_text=input_text, output_text=output_text, stdin=input_text + "\n", expected_stdout=output_text + "\n", parsed=False))
        if multi_line_input and not any(e.args is not None for e in examples):
            mode = "stdio"
            for example in examples:
                example.parsed = True
    else:
        for match in INLINE_ONE_LINE.finditer(full):
            names, values = parse_call_input(match.group("input"))
            ok, expected = literal(match.group("output"))
            if values is not None and ok:
                if names and not parameters:
                    parameters = names
                examples.append(ImportExample(input_text=match.group("input").strip(), output_text=match.group("output").strip(), args=values, expected=expected, parsed=True))
        for match in CALL_ARROW.finditer(full):
            names, values = parse_call_input(match.group(2))
            ok, expected = literal(match.group(3))
            if values is not None and ok:
                function_name = function_name or match.group(1)
                examples.append(ImportExample(input_text=f"{match.group(1)}({match.group(2)})", output_text=match.group(3).strip(), args=values, expected=expected, parsed=True))

    # Input and Output headings used as a single example, the common judge layout.
    if not examples and sections.get("input_format") and sections.get("output_format"):
        input_section, output_section = sections["input_format"], sections["output_format"]
        def looks_like_data(section: str) -> bool:
            return bool(section) and len(section) < 200 and not re.search(r"[a-z]{4,}\s+[a-z]{3,}", section)

        if looks_like_data(input_section) and looks_like_data(output_section):
            mode = "stdio"
            examples.append(ImportExample(input_text=input_section, output_text=output_section, stdin=input_section + "\n", expected_stdout=output_section + "\n", parsed=True))
            sections["input_format"] = ""
            sections["output_format"] = ""

    if mode == "function" and examples and not parameters:
        count = max((len(e.args or []) for e in examples), default=1)
        parameters = ["value"] if count == 1 else [f"arg{i + 1}" for i in range(count)]
        warnings.append("Parameter names were not given, so placeholder names were used. You can rename them.")

    description_parts = [sections.get("preamble", ""), sections.get("description", "")]
    description = "\n\n".join(p for p in description_parts if p).strip()
    description = re.split(r"\n\s*\**\s*(?:example|sample)\s*\d*\s*\**\s*:?\s*\n", description, maxsplit=1, flags=re.I)[0].strip()
    description = INLINE_EXAMPLE.sub("", description).strip()

    if function_name is None and mode == "function":
        solution_method = re.search(r"class\s+Solution.*?def\s+([A-Za-z_]\w*)\s*\(", full, flags=re.S)
        if solution_method:
            function_name = solution_method.group(1)
        else:
            function_name = _snake(title) if title else "solve"
            if examples:
                warnings.append(f"The function name was not given, so {function_name} was suggested. You can change it.")

    missing: list[str] = []
    if not title:
        missing.append("title")
    if len(description) < 15:
        missing.append("description")
    if not sections.get("constraints"):
        missing.append("constraints")
    if not examples:
        missing.append("examples")
    if not difficulty:
        missing.append("difficulty")
    unparsed = sum(1 for e in examples if not e.parsed)
    if unparsed:
        warnings.append(f"{unparsed} example(s) could not be read as test data. Please check them in the next step.")

    input_format = sections.get("input_format") or None
    output_format = sections.get("output_format") or None
    return ImportDraft(
        title=title[:160], description=description, constraints=sections.get("constraints") or None, input_format=input_format, output_format=output_format,
        difficulty=difficulty, tags=[], unit_id=suggest_unit(f"{title} {description}", []), mode=mode, function_name=function_name if mode == "function" else None,
        parameters=parameters if mode == "function" else [], examples=examples, missing_fields=missing, warnings=warnings,
    )


AUTO_STARTER_MARKERS = ("# Write your solution here", "# Read input with input()")


def generate_starter(draft: ImportDraft) -> str:
    """Starter code must always match the reviewed details, or the tests would call a missing function."""
    existing = (draft.starter_code or "").strip()
    if draft.mode == "stdio":
        if existing and "def " not in existing and not any(marker in existing for marker in AUTO_STARTER_MARKERS[:1]):
            return existing + "\n"
        return "# Read input with input() and print your answer.\nline = input()\n\n"
    params = ", ".join(draft.parameters)
    name = draft.function_name or "solve"
    header = f"def {name}({params}):"
    if existing and header in existing:
        return existing + "\n"
    return f"{header}\n    # Write your solution here\n    pass\n"
