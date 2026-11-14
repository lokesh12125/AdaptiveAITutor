"""Understand what the learner asked, and which code they asked about.

A learner can type what is confusing and point at part of their code. This module reads that request
and looks at those lines, using the AST and, where possible, a real trace from the sandbox showing what
the variables held. So an answer can say what actually happened, even with no language model configured.

Everything here is deterministic. The learner's text is data: it selects a kind of answer, and it can
never change the policy or the limits.
"""
from __future__ import annotations

import ast
import re
from typing import Any

from .contracts import DiagnosticOutput, FocusContext, LearnerQuestion, TraceRow

INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("solution_request", re.compile(r"\b(give me|show me|tell me|write|just give|send)\b.*\b(answer|solution|code|fix)\b|\b(solve|do) (it|this) for me\b|\bcomplete (solution|code)\b|\bfull (solution|code|answer)\b", re.I)),
    ("error_meaning", re.compile(r"\b(what|why).*\b(error|exception|invalid syntax|traceback)\b|\berror mean|\bwhat('?s| is) .*error\b", re.I)),
    ("explain_code", re.compile(r"\b(what does|what is this|explain|meaning of|what do(es)?)\b.*\b(line|this|code|loop|function|part|do|mean)\b|\bdon'?t (understand|get) (this|that|the|line|what|how|why)\b", re.I)),
    ("where_wrong", re.compile(r"\bwhere\b|\bwhich line\b|\bwhat('?s| is) wrong\b|\bfind (the|my) (bug|mistake|error)\b|\bmy (bug|mistake)\b", re.I)),
    ("why_fails", re.compile(r"\bwhy\b|\bnot working\b|\bdoesn'?t work\b|\bfail(s|ing|ed)?\b|\bwrong (answer|output|result)\b|\bincorrect\b", re.I)),
    ("how_start", re.compile(r"\bhow (do|can|should) i (start|begin|approach|solve)\b|\bwhere (do|should) i (start|begin)\b|\bno idea\b|\bhow to (start|begin|approach)\b|\bfirst step\b", re.I)),
    ("next_step", re.compile(r"\bwhat (next|now|should i do)\b|\bnext step\b|\bwhat do i do\b", re.I)),
]
STUCK_WORDS = re.compile(r"\b(stuck|confus\w*|lost|don'?t (understand|get)|no idea|frustrat\w*)\b", re.I)
LINE_REFERENCE = re.compile(r"\blines?\s+(\d+)(?:\s*(?:-|to|and|through)\s*(\d+))?\b", re.I)

CONCEPT_NOTES: dict[str, tuple[str, str]] = {
    # key: (explanation, the topic that teaches it)
    "range": ("`range(a, b)` gives a, a + 1, and so on, and stops before b. `range(n)` starts at 0 and also stops before n.", "loops"),
    "for loop": ("A `for` loop takes each item from a sequence in turn and runs its block once per item.", "loops"),
    "while": ("A `while` loop repeats as long as its condition is true, so something inside must eventually make it false.", "loops"),
    "if": ("`if` runs its block only when the condition is true. `elif` and `else` handle the other cases.", "conditionals"),
    "return": ("`return` hands a value back to the caller and ends the function straight away. Without it, the function gives back None.", "functions"),
    "print": ("`print` only shows a value on screen. It does not hand anything back, so tests of a function's result cannot see it.", "functions"),
    "function": ("A function is a named block of code. Parameters receive values when it is called, and `return` sends a result back.", "functions"),
    "indent": ("Python uses indentation to decide which lines belong to a block. Lines in one block start at the same column.", "python-basics"),
    "variable": ("A variable is a name for a value. `x = 5` stores 5 under the name x, and using `x` later reads it.", "variables-io"),
    "slice": ("`items[a:b]` makes a new sequence from position a up to, but not including, position b.", "strings"),
    "string": ("A string is text. It is indexed from 0 and cannot be changed in place, so methods return new strings.", "strings"),
    "list": ("A list holds items in order. It is indexed from 0, and `append` adds to the end.", "lists-dicts"),
    "dict": ("A dictionary maps keys to values. Reading a missing key raises KeyError, so `.get(key, default)` is often safer.", "lists-dicts"),
    "set": ("A set holds unique items and answers `x in s` very quickly, which makes it good for spotting repeats.", "hashing"),
    "recursion": ("A recursive function calls itself on a smaller input, and needs a base case that returns without calling itself.", "recursion"),
    "binary search": ("Binary search halves a sorted range each step by comparing with the middle value, so it takes about log n steps.", "searching-sorting"),
    "sort": ("`sorted(items)` returns a new sorted list, and `items.sort()` sorts in place. `key=` chooses what to compare.", "searching-sorting"),
    "two pointers": ("Two pointers walk through a sequence from different positions, often from both ends, to avoid a nested loop.", "arrays-two-pointers"),
    "sliding window": ("A sliding window keeps a range of items and updates it as it moves, rather than recomputing from scratch.", "arrays-two-pointers"),
    "hash": ("Hashing lets a dictionary or set find a key in about constant time, which turns many nested loops into one pass.", "hashing"),
    "stack": ("A stack is last in, first out. In Python a list works well, using `append` and `pop`.", "stacks-queues"),
    "queue": ("A queue is first in, first out. `collections.deque` gives fast `append` and `popleft`.", "stacks-queues"),
    "linked list": ("A linked list is a chain of nodes where each points to the next. Keep a reference before you change a link.", "linked-lists"),
    "tree": ("A binary tree node has a value and up to two children. Most tree code handles an empty node, then recurses on each child.", "trees"),
    "graph": ("A graph is nodes joined by edges, often stored as a dictionary of neighbours. A visited set stops you repeating nodes.", "graphs"),
    "dynamic programming": ("Dynamic programming solves overlapping smaller problems once, stores the results, and builds the answer from them.", "dynamic-programming"),
}
CONCEPT_ALIASES = {
    "for loop": ("for loop", "for-loop", "loop", "iterate"), "while": ("while",), "range": ("range",), "if": ("if statement", "condition", "elif", " else"), "return": ("return",), "print": ("print",),
    "function": ("function", "def ", "parameter", "argument"), "indent": ("indent",), "variable": ("variable",), "slice": ("slice", "slicing"), "string": ("string",), "list": (" list", "array", "append"),
    "dict": ("dict", "key"), "set": (" set",), "recursion": ("recurs", "base case"), "binary search": ("binary search",), "sort": ("sort",), "two pointers": ("two pointer", "two-pointer"), "sliding window": ("sliding window", "window"),
    "hash": ("hash",), "stack": ("stack",), "queue": ("queue", "deque"), "linked list": ("linked list", "listnode"), "tree": ("tree", "bst"), "graph": ("graph", "bfs", "dfs"), "dynamic programming": ("dynamic programming", " dp", "memo"),
}
# Checked in this order, so "binary search" wins over "search" style words and "for loop" over "for".
CONCEPT_ORDER = ["binary search", "sliding window", "two pointers", "dynamic programming", "linked list", "recursion", "range", "while", "for loop", "slice", "dict", "hash", "set", "stack", "queue", "tree", "graph", "sort", "return", "print", "indent", "if", "string", "list", "variable", "function"]

ERROR_MEANINGS = {
    "SyntaxError": "A syntax error means Python could not read the file at all, so none of your code ran. It is about how the line is written, not about your logic.",
    "IndentationError": "An indentation error means the spaces at the start of a line do not fit the block it belongs to. Python uses those spaces to understand your structure.",
    "TabError": "A tab error means tabs and spaces are mixed in the same block. Use spaces only.",
    "IndexError": "An IndexError means your code asked for a position that does not exist. For a list of length n, valid positions run from 0 to n - 1.",
    "KeyError": "A KeyError means your code read a dictionary key that is not there yet.",
    "TypeError": "A TypeError means an operation got a kind of value it cannot work with, such as adding text to a number or calling something that is not a function.",
    "NameError": "A NameError means Python met a name with no value yet. It is usually a spelling slip, or a variable used before it is assigned.",
    "UnboundLocalError": "An UnboundLocalError means this function assigns the variable somewhere, but reads it before that assignment runs.",
    "ValueError": "A ValueError means a function got the right kind of value, but with content it cannot use, such as `int('abc')`.",
    "ZeroDivisionError": "A ZeroDivisionError means your code divided by zero for this input.",
    "AttributeError": "An AttributeError means this value does not have that method or attribute. The value is often None, or not the type you expected.",
    "RecursionError": "A RecursionError means your function kept calling itself until Python stopped it, usually because a base case is missing or never reached.",
    "EOFError": "An EOFError means your code called `input()` when there was no more input to read.",
}


def read_question(text: str | None, self_state: str | None = None) -> LearnerQuestion | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return LearnerQuestion(text="", intent="overwhelmed") if self_state == "overwhelmed" else None
    intent = "general"
    if self_state == "overwhelmed":
        intent = "overwhelmed"
    else:
        for name, pattern in INTENT_PATTERNS:
            if pattern.search(cleaned):
                intent = name
                break
    lowered = f" {cleaned.lower()} "
    concept = next((key for key in CONCEPT_ORDER if any(alias in lowered for alias in CONCEPT_ALIASES[key])), None)
    if intent == "general" and concept and re.search(r"\b(what|how|explain|mean|work|use|difference)\b", lowered):
        intent = "concept"
    return LearnerQuestion(text=cleaned[:500], intent=intent, concept=concept, stuck=bool(STUCK_WORDS.search(cleaned)))


def choose_focus(question_text: str | None, start: int | None, end: int | None, code: str) -> tuple[int, int] | None:
    """Selected lines win, then lines named in the question. Anything not in the code is ignored."""
    count = len(code.splitlines())
    if start is None:
        match = LINE_REFERENCE.search(question_text or "")
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
    end = start if end is None else end
    start, end = min(start, end), max(start, end)
    if start < 1 or start > count:
        return None
    return start, min(end, count, start + 14)


_KIND_WORDS = {
    "loop": "a loop, which repeats its block",
    "while": "a `while` loop, which repeats while its condition is true",
    "condition": "a condition, which decides whether its block runs",
    "return": "a `return`, which hands a value back and ends the function",
    "assignment": "an assignment, which stores the value on the right under the name on the left",
    "print": "a `print`, which shows a value but does not hand it back",
    "function": "a function definition, which runs only when the function is called",
    "call": "a function call",
}


def _kinds_by_ast(code: str, start: int, end: int) -> tuple[list[str], list[str]]:
    kinds: list[str] = []
    names: list[str] = []
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            line = getattr(node, "lineno", None)
            if line is None or not start <= line <= end:
                continue
            if isinstance(node, ast.For):
                kinds.append("loop")
            elif isinstance(node, ast.While):
                kinds.append("while")
            elif isinstance(node, ast.If):
                kinds.append("condition")
            elif isinstance(node, ast.Return):
                kinds.append("return")
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                kinds.append("assignment")
            elif isinstance(node, ast.FunctionDef):
                kinds.append("function")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                kinds.append("print")
            elif isinstance(node, ast.Call):
                kinds.append("call")
            elif isinstance(node, ast.Name) and node.id not in names:
                names.append(node.id)
    else:
        for raw in code.splitlines()[start - 1 : end]:
            first = raw.strip().split(" ")[0].rstrip(":") if raw.strip() else ""
            mapped = {"for": "loop", "while": "while", "if": "condition", "elif": "condition", "else": "condition", "return": "return", "def": "function", "print": "print"}.get(first.split("(")[0])
            if mapped:
                kinds.append(mapped)
            elif "=" in raw:
                kinds.append("assignment")
    # Order by importance, without repeats.
    order = ["function", "loop", "while", "condition", "return", "print", "assignment", "call"]
    return [k for k in order if k in kinds], names[:6]


def build_focus(code: str, span: tuple[int, int], diagnostic: DiagnosticOutput, auto: bool = False) -> FocusContext:
    start, end = span
    lines = [line.rstrip() for line in code.splitlines()[start - 1 : end]]
    kinds, names = _kinds_by_ast(code, start, end)
    error_line = diagnostic.evidence.line if diagnostic.category in ("syntax", "runtime") else None
    return FocusContext(
        start=start, end=end, lines=lines, kinds=kinds, names=names, auto=auto,
        contains_error=bool(error_line and start <= error_line <= end), error_elsewhere=bool(error_line and not start <= error_line <= end),
    )


def summarise_trace(events: list[dict[str, Any]] | None, input_text: str | None, count_line: int | None = None) -> tuple[list[TraceRow], int]:
    """Turn raw trace events into a value history per variable. `runs` is how often `count_line`, or the first traced line, ran."""
    if not events:
        return [], 0
    first_line = count_line if count_line and any(e.get("line") == count_line for e in events) else events[0].get("line")
    runs = sum(1 for event in events if event.get("line") == first_line)
    histories: dict[str, list[str]] = {}
    for event in events:
        for name, value in (event.get("vars") or {}).items():
            history = histories.setdefault(name, [])
            if not history or history[-1] != value:
                history.append(value)
    # Variables that change are the interesting ones, so they come first.
    ordered = sorted(histories.items(), key=lambda item: -len(item[1]))
    return [TraceRow(name=name, values=values[:6], more=len(values) > 6) for name, values in ordered[:5]], runs


def _lines_label(focus: FocusContext) -> str:
    return f"line {focus.start}" if focus.start == focus.end else f"lines {focus.start} to {focus.end}"


def _describe_lines(focus: FocusContext) -> str:
    label = _lines_label(focus)
    label = label[0].upper() + label[1:]
    quoted = f"`{focus.lines[0].strip()[:70]}`" if focus.lines and focus.start == focus.end and focus.lines[0].strip() else ""
    subject = f"{label}, {quoted}," if quoted else label
    if not focus.kinds:
        return f"{subject} has no statement to run." if not "".join(focus.lines).strip() else f"{subject} is what you pointed at."
    described = _KIND_WORDS[focus.kinds[0]]
    verb = "is" if focus.start == focus.end else "includes"
    sentence = f"{subject} {verb} {described}."
    if focus.lines and "range(" in " ".join(focus.lines):
        sentence += " `range(a, b)` stops before b."
    return sentence


def _describe_trace(focus: FocusContext) -> str:
    example = focus.trace_input or "the example"
    if focus.trace_never_ran:
        return f"When I ran {example}, {_lines_label(focus)} never ran, so the code must return or skip past it first."
    if not focus.trace:
        return ""
    times = "once" if focus.trace_runs == 1 else f"{focus.trace_runs} times"
    rows = []
    for row in focus.trace:
        if len(row.values) > 1:
            rows.append(f"- `{row.name}` was " + ", then ".join(row.values) + (", and more" if row.more else ""))
        else:
            rows.append(f"- `{row.name}` stayed {row.values[0]}")
    return f"When I ran {example}, {_lines_label(focus)} ran {times}:\n" + "\n".join(rows)


def _names(names: list[str]) -> str:
    quoted = [f"`{name}`" for name in names]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def _what_changed(focus: FocusContext) -> str:
    """What moved and what did not is often the clearest clue, and it is an observation, not an opinion."""
    if focus.trace_runs < 2:
        return ""
    changing = [row.name for row in focus.trace if len(row.values) > 1]
    steady = [row.name for row in focus.trace if len(row.values) == 1]
    if not changing or not steady:
        return ""
    return f"Over those {focus.trace_runs} passes {_names(changing)} changed, while {_names(steady)} stayed the same. Is that what you intended?"


def _explain_line(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    if text.startswith("#"):
        return "is a comment, which Python ignores"
    body = text.rstrip(":").strip()
    match = re.match(r"for\s+(.+?)\s+in\s+(.+)", body)
    if match:
        return f"takes each item from `{match.group(2)}` in turn, as `{match.group(1)}`"
    for keyword, meaning in (("while", "repeats its block while `{}` is true"), ("if", "runs its block only when `{}` is true"), ("elif", "runs its block when `{}` is true and the checks above were not"), ("return", "hands a value back and ends the function")):
        if body.startswith(f"{keyword} "):
            return meaning.format(body[len(keyword) + 1 :].strip())
    if body == "else":
        return "runs its block when the checks above were not true"
    if body == "return":
        return "ends the function and hands back None"
    if body in ("break", "continue"):
        return "leaves the loop straight away" if body == "break" else "skips to the next pass of the loop"
    match = re.match(r"def\s+(\w+)", body)
    if match:
        return f"defines the function `{match.group(1)}`, which runs only when it is called"
    if body.startswith("print("):
        return "shows a value on screen, but does not hand it back"
    match = re.match(r"([A-Za-z_][\w.\[\], ]*?)\s*([-+*/%]{1,2})=\s*(.+)", body)
    if match:
        return f"updates `{match.group(1)}`, changing it by `{match.group(3)}`"
    match = re.match(r"([A-Za-z_][\w.\[\], ]*?)\s*=(?!=)\s*(.+)", body)
    if match:
        return f"works out `{match.group(2)}` and stores it in `{match.group(1)}`"
    return "runs this statement"


def _line_by_line(focus: FocusContext) -> str:
    rows = []
    for offset, raw in enumerate(focus.lines[:6]):
        meaning = _explain_line(raw)
        if meaning:
            rows.append(f"- Line {focus.start + offset}, `{raw.strip()[:70]}`, {meaning}")
    return "\n".join(rows)


def _join(parts: list[str]) -> str:
    """One paragraph, with lists kept on their own lines."""
    text = ""
    for part in dict.fromkeys(part for part in parts if part):
        if not text:
            text = part
        elif "\n- " in part or part.startswith("- ") or "\n- " in text.rsplit("\n\n", 1)[-1] or text.rsplit("\n\n", 1)[-1].startswith("- "):
            text += f"\n\n{part}"
        else:
            text += f" {part}"
    return text


NOT_RAN_CLEANLY = ("syntax", "runtime", "timeout", "memory", "output_limit", "accepted", "service_failure", "no_tests", "cancelled")


def _result_sentence(diagnostic: DiagnosticOutput) -> str:
    example = diagnostic.evidence.failing_example
    if example and example.got is not None:
        return f"The result was {example.got}, and {example.expected} was expected."
    return ""


def _next_action(diagnostic: DiagnosticOutput, focus: FocusContext | None) -> str:
    evidence = diagnostic.evidence
    if diagnostic.category == "syntax":
        where = f"line {evidence.line}" if evidence.line else "the marked line"
        return f"Fix {where} first, because nothing else can run until Python can read the file."
    if diagnostic.category == "accepted":
        return "All the tests pass, so there is nothing to correct here."
    if focus and focus.trace and evidence.failing_example and evidence.failing_example.got is not None:
        return "Are those the values this input needs at that point?"
    if focus and focus.error_elsewhere and evidence.line:
        return f"Look at line {evidence.line} next, since that is where Python reported the problem."
    if diagnostic.category == "runtime" and evidence.line:
        return f"Check what each value on line {evidence.line} holds just before that line runs."
    if diagnostic.category in ("timeout", "memory", "output_limit"):
        return "Check what changes on each pass, and whether it moves towards stopping."
    if evidence.failing_example and evidence.failing_example.input:
        return f"Try working through {evidence.failing_example.input} by hand, and note the first value that differs."
    return "Select the lines you are least sure about, and ask again, so I can show what they actually do."


def _opening(question: LearnerQuestion, focus: FocusContext | None) -> str:
    if question.intent == "solution_request":
        return "I will not write the solution, because working it out is what makes it stick. Here is what I can show you instead."
    if question.intent == "overwhelmed":
        return "That is completely fine. Forget the rest for a moment, and do just one thing."
    if question.stuck and not focus:
        return "Let us narrow this down to one thing."
    return ""


def _error_facts(diagnostic: DiagnosticOutput) -> list[str]:
    evidence = diagnostic.evidence
    parts = [ERROR_MEANINGS.get(evidence.error_type or "", "")]
    if evidence.line:
        quoted = f": `{evidence.source_line}`" if evidence.source_line else ""
        parts.append(f"Python reported it on line {evidence.line}{quoted}.")
    return parts


def _evidence_angle(diagnostic: DiagnosticOutput) -> str:
    """What the code actually did: the lines, the values, and the result."""
    question = diagnostic.question or LearnerQuestion(text="", intent="general")
    focus = diagnostic.focus
    evidence = diagnostic.evidence
    parts: list[str] = []
    if question.intent == "concept" and question.concept:
        parts.append(CONCEPT_NOTES[question.concept][0])
    if question.intent == "error_meaning" or (question.intent in ("why_fails", "where_wrong", "general", "explain_code") and diagnostic.category in ("syntax", "runtime") and not focus):
        parts.extend(_error_facts(diagnostic))
    if focus:
        parts.append(_describe_lines(focus))
        if focus.error_elsewhere and diagnostic.category == "syntax":
            parts.append(f"Your file has a syntax error on line {evidence.line}, so these lines have not run yet.")
        elif focus.contains_error and evidence.error_type:
            parts.append(f"This is where Python reported {evidence.error_type}.")
        parts.append(_describe_trace(focus))
    if diagnostic.category not in ("syntax", "accepted") and question.intent != "concept":
        parts.append(_result_sentence(diagnostic))
    if question.intent == "how_start" and diagnostic.issue_key == "logic:not_implemented":
        parts.append("Work out the first example by hand and write your steps as comments. Then turn just one comment into code.")
    elif question.intent == "concept" and question.concept and not focus:
        parts.append("See the lesson for this topic for worked examples you can run.")
    else:
        parts.append(_next_action(diagnostic, focus))
    return _join(parts)


def _compare_angle(diagnostic: DiagnosticOutput) -> str:
    """Where to look: how the result differs, and what moved."""
    focus = diagnostic.focus
    example = diagnostic.evidence.failing_example
    parts: list[str] = []
    if diagnostic.category in ("syntax", "runtime"):
        parts.extend(_error_facts(diagnostic))
    elif diagnostic.category not in NOT_RAN_CLEANLY:
        parts.append("Python reported no error here, so your code runs and its logic gives a different answer.")
    if example and example.got is not None:
        parts.append(f"For {example.input} it gave {example.got}, and {example.expected} was expected.")
    if focus and focus.trace:
        parts.append(_what_changed(focus) or _describe_trace(focus))
    if diagnostic.category not in ("syntax", "accepted") and example and example.input:
        parts.append("Work through that input by hand. The first value that differs from what your code holds is where to look.")
    return _join(parts)


def _start_angle(diagnostic: DiagnosticOutput) -> str:
    example = diagnostic.evidence.failing_example
    parts = [f"This problem practises {diagnostic.technique}" if diagnostic.technique else ""]
    if diagnostic.technique and not diagnostic.technique.rstrip().endswith((".", "!", "?")):
        parts[0] += "."
    if example and example.input and example.expected is not None:
        parts.append(f"Start with {example.input}, where {example.expected} is expected. Work it out by hand and write your steps as comments.")
    else:
        parts.append("Start with the first example. Work it out by hand and write your steps as comments.")
    parts.append("Then turn just one comment into code, and run it.")
    return _join(parts)


def _explain_angle(diagnostic: DiagnosticOutput) -> str:
    focus = diagnostic.focus
    if not focus:
        return ""
    parts = [_line_by_line(focus)]
    if focus.lines and "range(" in " ".join(focus.lines):
        parts.append("`range(a, b)` stops before b.")
    if focus.error_elsewhere and diagnostic.category == "syntax":
        parts.append(f"Your file has a syntax error on line {diagnostic.evidence.line}, so these lines have not run yet.")
    elif focus.contains_error and diagnostic.evidence.error_type:
        parts.append(f"This is where Python reported {diagnostic.evidence.error_type}.")
    parts.append(_describe_trace(focus))
    return _join(parts)


def _error_angle(diagnostic: DiagnosticOutput) -> str:
    example = diagnostic.evidence.failing_example
    if diagnostic.evidence.error_type:
        return _join([*_error_facts(diagnostic), _next_action(diagnostic, diagnostic.focus)])
    if diagnostic.category not in NOT_RAN_CLEANLY:
        result = f", and gave {example.got} where {example.expected} was expected" if example and example.got is not None else ""
        return f"There is no Python error on this run. Your code ran to the end{result}, so this is about the logic rather than an error message."
    return ""


def _print_angle(diagnostic: DiagnosticOutput) -> str:
    focus = diagnostic.focus
    if not focus or diagnostic.category in ("syntax", "timeout", "memory", "output_limit", "accepted"):
        return ""
    names = [row.name for row in focus.trace][:3] or [name for name in focus.names if name not in ("print", "len", "range", "sum", "min", "max", "sorted", "int", "str", "list", "dict", "set")][:3]
    if not names:
        return ""
    return f"Try adding `print({', '.join(names)})` as a temporary line next to {_lines_label(focus)}, then press Run. Seeing the values on each pass shows where they stop matching what you expected."


def _next_step_angle(diagnostic: DiagnosticOutput) -> str:
    return _join([_next_action(diagnostic, diagnostic.focus), "Change just one thing, then run the examples again."])


_ANGLES = {
    "where_wrong": (_compare_angle, _evidence_angle, _print_angle, _explain_angle, _start_angle),
    "explain_code": (_explain_angle, _evidence_angle, _compare_angle, _print_angle),
    "how_start": (_start_angle, _next_step_angle, _evidence_angle, _print_angle),
    "next_step": (_next_step_angle, _print_angle, _compare_angle, _start_angle),
    "error_meaning": (_error_angle, _evidence_angle, _compare_angle),
    "overwhelmed": (_next_step_angle, _start_angle, _print_angle),
    "solution_request": (_start_angle, _evidence_angle, _compare_angle, _print_angle),
}
_DEFAULT_ANGLES = (_evidence_angle, _compare_angle, _print_angle, _explain_angle, _start_angle)


def answer_candidates(diagnostic: DiagnosticOutput) -> list[str]:
    """Different honest answers to this question, best first, built only from observed evidence.

    Asking again, or asking something else about the same code, can then get a new angle rather than a refusal.
    """
    question = diagnostic.question or LearnerQuestion(text="", intent="general")
    opening = _opening(question, diagnostic.focus)
    # A specific error or an empty function needs the evidence first, whatever words were used.
    angles = _ANGLES.get(question.intent, _DEFAULT_ANGLES)
    if question.intent == "how_start" and diagnostic.issue_key == "logic:not_implemented":
        angles = (_evidence_angle, _start_angle, _print_angle)
    found = [_join([opening, text]) for text in (angle(diagnostic) for angle in angles) if text]
    return list(dict.fromkeys(found))


def answer_question(diagnostic: DiagnosticOutput) -> str:
    """The best answer. A configured model may reword this kind of help, but only the evidence goes in."""
    candidates = answer_candidates(diagnostic)
    return candidates[0] if candidates else _next_action(diagnostic, diagnostic.focus)


def related_topic(diagnostic: DiagnosticOutput) -> str | None:
    question = diagnostic.question
    if question and question.concept:
        return CONCEPT_NOTES[question.concept][1]
    return None
