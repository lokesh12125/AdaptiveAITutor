"""Work out why an error happened, from the learner's own code, the error, and the task.

The raw message says what Python could not do. This module says what the learner was probably trying to do.
A NameError, for example, may be a missing import, a typo in a parameter, a method called like a function,
or a variable from another function. Each needs different help, and repeating the message helps with none of them.

Everything here is rule-based and reads only the learner's code, the task text and visible examples.
Hidden tests are never read for their contents. The result is a set of observations and a likely cause,
with a confidence. It is what the learner's code suggests, not a claim about what they were thinking.
"""
from __future__ import annotations

import ast
import builtins
import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from .contracts import ErrorDiagnosis

# ---------------------------------------------------------------- what Python knows

STANDARD_MODULES = {
    "math", "random", "collections", "itertools", "functools", "heapq", "bisect", "string", "re", "sys", "os", "json", "time", "datetime",
    "statistics", "decimal", "fractions", "copy", "operator", "typing", "dataclasses", "abc", "enum", "csv", "pathlib",
}
FROM_IMPORTS = {
    "sqrt": "math", "floor": "math", "ceil": "math", "gcd": "math", "lcm": "math", "factorial": "math", "isqrt": "math", "pi": "math", "log2": "math", "log10": "math", "hypot": "math",
    "Counter": "collections", "defaultdict": "collections", "deque": "collections", "namedtuple": "collections", "OrderedDict": "collections",
    "heappush": "heapq", "heappop": "heapq", "heapify": "heapq", "nlargest": "heapq", "nsmallest": "heapq",
    "bisect_left": "bisect", "bisect_right": "bisect", "insort": "bisect",
    "reduce": "functools", "lru_cache": "functools", "cache": "functools", "partial": "functools",
    "permutations": "itertools", "combinations": "itertools", "product": "itertools", "chain": "itertools", "accumulate": "itertools", "groupby": "itertools", "count": "itertools", "cycle": "itertools",
    "randint": "random", "choice": "random", "shuffle": "random", "dataclass": "dataclasses", "deepcopy": "copy", "ascii_lowercase": "string", "ascii_uppercase": "string", "digits": "string",
}
# name: (the kind of value it belongs to, the usual way to write it)
METHODS = {
    "count": ("list or string", "some_list.count(value)"), "index": ("list or string", "some_list.index(value)"),
    "append": ("list", "some_list.append(value)"), "extend": ("list", "some_list.extend(more)"), "insert": ("list", "some_list.insert(position, value)"),
    "remove": ("list", "some_list.remove(value)"), "pop": ("list", "some_list.pop()"), "sort": ("list", "some_list.sort()"), "reverse": ("list", "some_list.reverse()"),
    "split": ("string", "text.split()"), "join": ("string", "', '.join(parts)"), "strip": ("string", "text.strip()"), "upper": ("string", "text.upper()"), "lower": ("string", "text.lower()"),
    "replace": ("string", "text.replace(old, new)"), "startswith": ("string", "text.startswith(start)"), "endswith": ("string", "text.endswith(end)"), "find": ("string", "text.find(part)"),
    "isdigit": ("string", "text.isdigit()"), "isalpha": ("string", "text.isalpha()"), "title": ("string", "text.title()"), "capitalize": ("string", "text.capitalize()"),
    "keys": ("dictionary", "some_dict.keys()"), "values": ("dictionary", "some_dict.values()"), "items": ("dictionary", "some_dict.items()"), "get": ("dictionary", "some_dict.get(key, default)"),
    "add": ("set", "some_set.add(value)"), "discard": ("set", "some_set.discard(value)"),
}
BUILTIN_ALIASES = {
    "length": "len", "lenght": "len", "leng": "len", "size": "len", "printf": "print", "println": "print", "echo": "print", "write": "print", "string": "str", "integer": "int",
    "boolean": "bool", "array": "list", "dictionary": "dict", "maximum": "max", "minimum": "min", "absolute": "abs", "true": "True", "false": "False", "null": "None", "none": "None", "nil": "None",
}
BUILTIN_PURPOSE = {
    "len": "how many items something holds", "print": "to show a value on screen", "str": "to turn a value into text", "int": "to turn a value into a whole number", "bool": "True or False", "list": "a list",
    "dict": "a dictionary", "max": "the largest value", "min": "the smallest value", "abs": "the size of a number without its sign", "True": "a true value", "False": "a false value", "None": "no value at all",
    "sum": "to add up values", "range": "a run of numbers", "input": "to read a line of input", "sorted": "a sorted copy", "float": "to turn a value into a decimal",
}
BUILTIN_NAMES = {name for name in dir(builtins) if not name.startswith("_")}
# Words in a task that show what the learner may be trying to do.
GOAL_WORDS = {
    "count": r"\b(how many|counts?|number of|occurrences?|times)\b", "sum": r"\b(sum|total|add up)\b", "max": r"\b(largest|biggest|maximum|highest)\b", "min": r"\b(smallest|lowest|minimum)\b",
    "sort": r"\b(sort|sorted|ascending|descending|in order)\b", "len": r"\b(length|how long|characters)\b", "reverse": r"\brevers", "unique": r"\b(unique|distinct|duplicates?)\b",
}
NAME_CAUSES = {"missing_import", "method_as_function", "builtin_misnamed", "misspelled", "parameter_typo", "used_before_assignment", "other_scope", "missing_function", "undefined_variable"}


@dataclass
class Use:
    node: ast.Name | None = None
    called: bool = False
    call: str | None = None
    args: list[str] = field(default_factory=list)
    attribute: str | None = None
    loop_target: str | None = None
    line: int | None = None


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _find_use(tree: ast.AST, name: str, line: int | None) -> Use:
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]
    chosen = next((n for n in nodes if n.lineno == line), nodes[0] if nodes else None)
    if chosen is None:
        return Use(line=line)
    parents = _parents(tree)
    use = Use(node=chosen, line=chosen.lineno)
    parent = parents.get(chosen)
    if isinstance(parent, ast.Attribute):
        use.attribute = parent.attr
        outer = parents.get(parent)
        if isinstance(outer, ast.Call) and outer.func is parent:
            use.call = ast.unparse(outer)[:60]
    elif isinstance(parent, ast.Call) and parent.func is chosen:
        use.called = True
        use.call = ast.unparse(parent)[:60]
        use.args = [ast.unparse(arg)[:30] for arg in parent.args]
    climb: ast.AST | None = chosen
    while climb is not None:
        above = parents.get(climb)
        if isinstance(above, ast.For) and above.iter is climb:
            use.loop_target = ast.unparse(above.target)
            break
        if isinstance(above, ast.stmt) and not isinstance(above, ast.For):
            break
        climb = above
    return use


def _created_in(scope: ast.AST) -> dict[str, int]:
    """Names a function or module creates directly, with the line of the first one. Nested functions keep their own."""
    names: dict[str, int] = {}

    def note(name: str, line: int) -> None:
        names[name] = min(line, names.get(name, line))

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                note(child.name, child.lineno)
                continue
            if isinstance(child, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                note(child.id, child.lineno)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for alias in child.names:
                    note((alias.asname or alias.name).split(".")[0], child.lineno)
            elif isinstance(child, ast.ExceptHandler) and child.name:
                note(child.name, child.lineno)
            visit(child)

    visit(scope)
    return names


def _functions(tree: ast.AST) -> list[ast.FunctionDef]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _enclosing(tree: ast.AST, line: int | None) -> ast.FunctionDef | None:
    if line is None:
        return None
    inside = [f for f in _functions(tree) if f.lineno <= line <= (f.end_lineno or f.lineno)]
    return max(inside, key=lambda f: f.lineno) if inside else None


def _params(function: ast.FunctionDef | None) -> list[str]:
    if function is None:
        return []
    arguments = function.args
    return [a.arg for a in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]] + ([arguments.vararg.arg] if arguments.vararg else []) + ([arguments.kwarg.arg] if arguments.kwarg else [])


def _closest(name: str, candidates: list[str], cutoff: float = 0.75) -> str | None:
    lowered = {c.lower(): c for c in candidates}
    if name.lower() in lowered and lowered[name.lower()] != name:
        return lowered[name.lower()]
    matches = difflib.get_close_matches(name, [c for c in candidates if c != name], n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _task_says(problem: dict[str, Any], kind: str | None) -> str | None:
    """The sentence in the task that shows what this tool might be for."""
    pattern = GOAL_WORDS.get(kind or "")
    if not pattern:
        return None
    text = re.sub(r"[`*_]", "", problem.get("description") or "")
    for sentence in re.split(r"(?<=[.?!])\s+", text):
        if re.search(pattern, sentence, re.I):
            return sentence.strip()[:120]
    return None


def _goal(name: str, use: Use, problem: dict[str, Any], evidence: list[str]) -> tuple[str | None, str | None]:
    """What the learner seems to want, read from the task, the function's name, the arguments and the structure."""
    kind = name if name in GOAL_WORDS else ("len" if name in ("length", "size") else None)
    says = _task_says(problem, kind)
    function_name = problem.get("function_name") or ""
    if kind and kind in function_name.lower():
        evidence.append(f"The function you are writing is called {function_name}.")
    if says:
        evidence.append(f'The task says: "{says}"')
    if use.args:
        evidence.append(f"It is given {', '.join(use.args[:3])}.")
    if use.loop_target:
        evidence.append(f"It supplies the values for the loop variable {use.loop_target}.")
    return kind, says


# ---------------------------------------------------------------- name errors

def _named_in(message: str) -> str | None:
    match = re.search(r"name '(\w+)' is not defined", message or "") or re.search(r"local variable '(\w+)'", message or "") or re.search(r"variable '(\w+)'", message or "")
    return match.group(1) if match else None


def _name_result(cause: str, name: str, line: int | None, likely: str, concept: str, confidence: float, evidence: list[str], **details: Any) -> ErrorDiagnosis:
    where = f" on line {line}" if line else ""
    return ErrorDiagnosis(
        error_class="name_resolution", cause=cause, likely_cause=likely, concept=concept, location=line, evidence=[f"{name} is used{where}, and Python could not find it.", *evidence], confidence=confidence,
        explanation=f'Python cannot find anything named "{name}"{where}.', name=name, **details,
    )


def analyse_name_error(code: str, error: dict[str, Any], problem: dict[str, Any]) -> ErrorDiagnosis | None:
    message = error.get("message") or ""
    name = _named_in(message)
    line = error.get("line")
    if not name:
        return None
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return _name_result("undefined_variable", name, line, f"{name} has no value when this line runs.", "Variables and names", 0.5, [])
    use = _find_use(tree, name, line)
    line = line or use.line
    enclosing = _enclosing(tree, line)
    params = _params(enclosing)
    here = _created_in(enclosing) if enclosing else _created_in(tree)
    module_names = _created_in(tree)
    evidence: list[str] = []
    kind, says = _goal(name, use, problem, evidence)
    common = {"call": use.call, "goal": says, "goal_kind": kind, "target": use.loop_target, "args": use.args}

    # Created in this same scope, but only further down.
    created = here.get(name)
    if created is not None and line is not None and created > line or error.get("type") == "UnboundLocalError":
        first = created if created is not None and line is not None and created > line else None
        if first is not None:
            evidence.append(f"{name} first gets a value on line {first}.")
        return _name_result("used_before_assignment", name, line, f"{name} is read before the line that gives it a value has run.", "Order of execution and variables", 0.95, evidence, defined_at=first, **common)

    # A module used with a dot, with no import.
    if use.attribute and name in STANDARD_MODULES:
        evidence.append(f"{name} is a module in Python's standard library, and no line imports it.")
        return _name_result("missing_import", name, line, f"The {name} module is used without being imported.", "Importing modules", 0.97, evidence, module=name, variant="module", **{**common, "call": use.call or f"{name}.{use.attribute}"})

    module = FROM_IMPORTS.get(name)
    looks_like_counter = name != "count" or (use.called and (use.loop_target is not None or len(use.args) == 2 or not use.args))
    if module and looks_like_counter and (use.called or name in ("pi", "digits", "ascii_lowercase", "ascii_uppercase")):
        imported_module = module in module_names
        evidence.append(f"{name} lives in Python's {module} module, and your code has not imported that name.")
        variant = "prefix" if imported_module else ("counter" if name == "count" else "function")
        return _name_result("missing_import", name, line, f"{name} comes from the {module} module, and it has not been imported.", "Importing tools from the standard library", 0.9, evidence, module=module, variant=variant, **common)

    if name in METHODS and use.called and use.args:
        owner, form = METHODS[name]
        evidence.append(f"In Python, {name} is a method of a {owner}, written after the value with a dot.")
        return _name_result("method_as_function", name, line, f"{name} is being called as a standalone function, but it is a method of a {owner}.", "Methods and how to call them", 0.88, evidence, owner=owner, form=form, receiver=use.args[0], **common)

    alias = BUILTIN_ALIASES.get(name) or _closest(name, sorted(BUILTIN_PURPOSE), 0.8)
    if alias:
        evidence.append(f"Python's name for this is {alias}.")
        return _name_result("builtin_misnamed", name, line, f"{name} looks like Python's built-in {alias}, under a different spelling.", "Built-in functions and exact names", 0.9, evidence, suggestion=alias, purpose=BUILTIN_PURPOSE.get(alias, "this"), **common)

    # A near match among names of the right sort. A function call is not a typo of a plain variable.
    functions_known = sorted({f.name for f in _functions(tree)})
    variables_known = sorted(({*here, *module_names, *params}) - set(functions_known))
    close = _closest(name, functions_known if use.called else [*params, *variables_known])
    if close:
        if close in params:
            evidence.append(f"{close} is a parameter of {enclosing.name if enclosing else 'this function'}.")
            return _name_result("parameter_typo", name, line, f"{name} looks like a misspelling of the parameter {close}.", "Function parameters and exact names", 0.9, evidence, suggestion=close, where=enclosing.name if enclosing else None, **common)
        first = {**module_names, **here}.get(close)
        evidence.append(f"Your code creates {close}" + (f" on line {first}." if first else "."))
        return _name_result("misspelled", name, line, f"{name} looks like a misspelling of {close}.", "Variables and exact names", 0.85, evidence, suggestion=close, defined_at=first, known=sorted(here)[:8], **common)

    for function in _functions(tree):
        if function is enclosing:
            continue
        theirs = _created_in(function)
        if name in theirs or name in _params(function):
            first = theirs.get(name, function.lineno)
            evidence.append(f"{name} exists inside {function.name}, starting on line {first}.")
            return _name_result("other_scope", name, line, f"{name} belongs to the function {function.name}, so this part of the code cannot see it.", "Scope: where a name is visible", 0.9, evidence, where=function.name, defined_at=first, **common)

    if use.called:
        return _name_result("missing_function", name, line, f"{name} is called, but it is never defined and is not part of Python.", "Defining and calling functions", 0.75, evidence, **common)
    return _name_result("undefined_variable", name, line, f"No line in your code gives {name} a value.", "Variables and assignment", 0.75, evidence, known=sorted(here)[:8], **common)


NAME_HINTS: dict[str, dict[str, Any]] = {
    "missing_import": {
        "conceptual_question": "Python cannot find anything named `{name}` on line {line}, because nothing in your code creates or imports it. What do you want `{call}` to do here, and where does that tool live in Python?",
        "targeted_hint": "`{name}` is not built into Python. It lives in the `{module}` module, so your code must import it before line {line} runs. Which line at the top of your file would do that?",
        "name_options": "You can write `import {module}` and then call `{module}.{name}(...)`. Or you can write `from {module} import {name}` and call `{name}(...)`. Both work, so which reads better to you?",
        "step_outline": "1. Go to the very top of your file, above any `def`.\n2. Add an import line for `{name}` from the `{module}` module.\n3. Check that the name on line {line} matches how you imported it.\n4. Press Run and see whether the error has gone.",
        "analogous_example": ("Here is an import on a different task. The import sits at the top, and the name can then be used anywhere below it.", "from math import floor\n\ndef whole_part(value):\n    return floor(value)", "Which module holds `{name}`, and what does your file need at the top?"),
        "direct_pointer": "Add `from {module} import {name}` as the first line of your file, above any `def`.",
    },
    "missing_import:module": {
        "conceptual_question": "Python does not know what `{name}` is on line {line}, because it has not been loaded yet. What has to happen before you can use a module's tools?",
        "targeted_hint": "`{name}` is a module in Python's standard library. Your code uses it on line {line}, but no line imports it. Which statement loads a module?",
        "name_options": "Modules stay unloaded until you ask for them, which keeps programs quick to start. You can load the whole module with `import {name}`, or take one tool with `from {name} import ...`. Which suits `{call}`, as you have written it?",
        "direct_pointer": "Add `import {name}` as the first line of your file, above any `def`.",
    },
    "missing_import:prefix": {
        "conceptual_question": "You imported `{module}`, but line {line} uses `{name}` on its own. How do you reach a tool that lives inside a module?",
        "targeted_hint": "`import {module}` loads the module, and its tools stay inside it. So Python only finds this one as `{module}.{name}`. How should line {line} be written?",
        "name_options": "You have two options. Keep your import and write `{module}.{name}(...)` on line {line}. Or change the import to `from {module} import {name}`, and keep the line as it is. Which do you prefer?",
        "direct_pointer": "On line {line}, write `{module}.{name}` instead of `{name}`, or change your import to `from {module} import {name}`.",
    },
    "missing_import:counter": {
        "conceptual_question": "Python cannot find anything named `{name}` in your code, and line {line} uses `{call}` to supply values for `{target}`. Which numbers should `{target}` take, and which Python tool could produce them?",
        "targeted_hint": "`{call}` looks like `itertools.count`, which counts upward from a start in fixed steps. It lives in a module, so Python only knows it after an import. Another tool, `range(start, stop, step)`, needs no import, so which suits this task?",
        "name_options": "These two tools differ in one way that matters. `itertools.count` keeps counting forever, so your loop needs its own stopping check, while `range` is told where to stop up front. Write down the values `{target}` should take for {example}, then choose.",
        "step_outline": "1. Write down the values `{target}` should take for {example}.\n2. Decide between `itertools.count` and `range(start, stop, step)`.\n3. For `itertools.count`, add its import at the very top of your file.\n4. For `range`, work out the stop value so the last number is included.\n5. Run your code and compare.",
        "analogous_example": ("Here are both tools on a different task. Notice the import at the top, and how each loop stops.", "from itertools import count\n\ndef first_power_of_two_above(limit):\n    for power in count(1):\n        if 2 ** power > limit:\n            return 2 ** power\n\ndef even_numbers_up_to(limit):\n    return list(range(2, limit + 1, 2))", "Which of these shapes fits your task, and what does your file still need?"),
        "direct_pointer": "Add `from itertools import count` as the first line of your file. Or change line {line} to use `range` with a start, a stop and a step, which needs no import.",
    },
    "method_as_function": {
        "conceptual_question": "Python cannot find a function named `{name}` in your code. What are you trying to do with `{receiver}`, and which Python tool could do that?",
        "targeted_hint": "You are calling `{name}` as a standalone function. In Python, `{name}` is a {owner} method, written after the value, as in `{form}`. So what belongs before the dot in your code?",
        "name_options": "Look at `{call}` on line {line}. A method is written after the value it works on, like `value.{name}(...)`, and anything else it needs goes inside the brackets. So which part of your call belongs before the dot, and which stays inside?",
        "step_outline": "1. Find `{call}` on line {line}.\n2. Decide which value `{name}` should work on.\n3. Move that value in front of the name, followed by a dot.\n4. Keep only the remaining values inside the brackets.\n5. Run your code and compare.",
        "analogous_example": ("Here are methods on a different task. The value comes first, then a dot, then the method.", "words = 'red green blue'.split()\nwords.append('gold')\nprint(words)", "What goes before the dot when you use `{name}`?"),
        "direct_pointer": "On line {line}, write it as `{receiver}.{name}(...)`. The value goes before the dot, and only what else it needs goes inside the brackets.",
    },
    "method_as_function:count": {
        "conceptual_question": "Python cannot find a function named `count` in your code. What are you trying to count, and which Python tool or loop could do that?",
        "targeted_hint": "You are calling `count` as a standalone function. In Python, `count` is often a list method, such as `some_list.count(value)`. Alternatively, how could you use a loop and a counter to count matching values?",
        "name_options": "There are two good ways to count. `some_list.count(value)` counts one exact value, and a loop with a counter can count by any rule, such as even numbers only. Does your task need one exact value, or a rule?",
        "step_outline": "1. Say exactly what you are counting, using {example}.\n2. If it is one exact value, call `.count(value)` on the list.\n3. If it is a rule, start a counter at 0 and loop over the items.\n4. Add one when an item matches the rule.\n5. Return the counter, then run your code.",
        "analogous_example": ("Here are both ways to count, on a different task.", "letters = ['a', 'b', 'a']\nprint(letters.count('a'))\n\nvowels = 0\nfor letter in 'banana':\n    if letter in 'aeiou':\n        vowels += 1\nprint(vowels)", "Which of these two ways of using `count` fits what your task counts?"),
        "direct_pointer": "Replace `{call}` on line {line}. If you need one exact value, write `{receiver}.count(value)`. If you need a rule, start a counter at 0 and add one inside a loop.",
    },
    "builtin_misnamed": {
        "conceptual_question": "Python has nothing called `{name}`. You seem to want {purpose}. What is Python's own name for that?",
        "targeted_hint": "Python's name for this is `{suggestion}`, not `{name}`. Python names must match exactly, including capital letters. Where does your line {line} need to change?",
        "name_options": "Compare `{name}` on line {line} with the built-in name `{suggestion}`. Many languages use different words for the same idea, so this is an easy slip. Are there any other places in your code that use the same word?",
        "step_outline": "1. Find every use of `{name}` in your code.\n2. Change each one to `{suggestion}`.\n3. Check the capital letters match exactly.\n4. Run your code again.",
        "analogous_example": ("Here are some of Python's built-in names, on a different task.", "words = ['a', 'bb']\nprint(len(words))\nprint(max(1, 2))\nfound = True", "Which of Python's names should replace `{name}`?"),
        "direct_pointer": "On line {line}, change `{name}` to `{suggestion}`.",
    },
    "misspelled": {
        "conceptual_question": "Python does not recognise `{name}` on line {line}. Compare it letter by letter with the names your code does create. Which one did you mean?",
        "targeted_hint": "Your code creates `{suggestion}`{defined_clause}, but line {line} uses `{name}`. Python treats those as two different names. Which spelling did you intend?",
        "name_options": "Python is exact about spelling and capital letters, so `{name}` and `{suggestion}` are unrelated to it. Pick one spelling for this value, and use it everywhere it appears. How many places need to change?",
        "step_outline": "1. Find where the value is first created.\n2. Copy that exact name.\n3. Find every use of it, including `{name}` on line {line}.\n4. Make each one match exactly.\n5. Run your code again.",
        "analogous_example": ("Here is a slip like this one on a different task. The two names look alike, and Python treats them as unrelated.", "# NameError: `totel` is not `total`\ntotal = 0\ntotal = totel + 1\n\n# Works: both names match\ntotal = 0\ntotal = total + 1", "Which name should `{name}` on your line {line} match?"),
        "direct_pointer": "On line {line}, change `{name}` to `{suggestion}`.",
    },
    "parameter_typo": {
        "conceptual_question": "Line {line} uses `{name}`, but your function's first line names what it receives. Do those names match exactly?",
        "targeted_hint": "`{where}` receives a parameter called `{suggestion}`, but line {line} reads `{name}`. Only the exact parameter name holds the value that was passed in. Which should change?",
        "name_options": "You can rename the parameter on the `def` line to `{name}`, or change `{name}` to `{suggestion}` on line {line}. Either works if every use matches. Which name describes this value better?",
        "step_outline": "1. Read the parameter names on the `def` line.\n2. Find every place the function body uses that value, including `{name}`.\n3. Make each one match the parameter exactly.\n4. Run your code again.",
        "analogous_example": ("Here is a function on a different task. Its body uses exactly the name on its `def` line.", "def shout(words):\n    return words.upper()", "Does `{name}` in your function match its `def` line in the same way?"),
        "direct_pointer": "On line {line}, change `{name}` to `{suggestion}`, which is the name on your `def` line.",
    },
    "used_before_assignment": {
        "conceptual_question": "On line {line} your code reads `{name}`, but does it have a value yet at that moment? Which line gives it its first value?",
        "targeted_hint": "{first_clause} Python runs lines from top to bottom, so `{name}` has no value yet at line {line}. What should it hold at the start?",
        "name_options": "You can fix this in two ways. Give `{name}` a starting value above line {line}, or move the line that sets it above line {line}. Which matches what your code means to do?",
        "step_outline": "1. Find the first line that gives `{name}` a value.\n2. Check whether line {line} can run before it.\n3. Decide what `{name}` should hold at the very start.\n4. Set that value above line {line}.\n5. Run your code again.",
        "analogous_example": ("Here is a running total on a different task. The starting value is set before the loop reads it.", "def letters_in(words):\n    letters = 0\n    for word in words:\n        letters += len(word)\n    return letters", "What is the starting value of your `{name}`, and is it set early enough?"),
        "direct_pointer": "Give `{name}` a starting value on a line above line {line}, such as where the function begins.",
    },
    "other_scope": {
        "conceptual_question": "`{name}` exists inside the function `{where}`, but line {line} is outside it. Can code outside a function see that function's variables?",
        "targeted_hint": "`{name}` is created inside `{where}`, on line {defined_at}. A function's variables are private to it, so line {line} cannot see them. How could that value get from one place to the other?",
        "name_options": "A value like `{name}` usually travels in one of two ways. A function can hand it back with `return`, and the caller can store it. Or the caller can pass it in as an argument. Which direction does it need to go?",
        "step_outline": "1. Decide which function should own the value.\n2. Have `{where}` return `{name}`, if the value needs to come out.\n3. Store the result in a variable where you call it.\n4. Pass it as an argument, if the value needs to go in.\n5. Run your code again.",
        "analogous_example": ("Here is a value moving between functions, on a different task. It leaves with `return`, and it arrives as an argument.", "def area(width, height):\n    return width * height\n\ndef describe(width, height):\n    size = area(width, height)\n    return f'Size {size}'", "Where does your `{name}` need to go?"),
        "direct_pointer": "Have `{where}` end with `return {name}`, and store the result where you need it. Or pass `{name}` in as an argument.",
    },
    "missing_function": {
        "conceptual_question": "Line {line} calls `{name}`, but your code never defines it, and it is not part of Python. What should `{call}` do?",
        "targeted_hint": "`{call}` on line {line} needs a function called `{name}`, and none exists yet. You could write it yourself with `def`, above where it is called, or do that work directly on this line. Which feels clearer?",
        "name_options": "A helper is a good idea when the same step is needed more than once, or has a clear name of its own. If it is one small step, it can stay inline. Which is true of `{name}` here?",
        "step_outline": "1. Say in one sentence what `{name}` should give back.\n2. Add `def {name}(...)` above the code that calls it.\n3. List what it needs as parameters.\n4. Write its body, and `return` the result.\n5. Run your code again.",
        "analogous_example": ("Here is a helper on a different task. It is defined once, and then called by name.", "def is_vowel(letter):\n    return letter in 'aeiou'\n\ndef vowels_in(word):\n    return [letter for letter in word if is_vowel(letter)]", "What would your `{name}` receive, and what would it give back?"),
        "direct_pointer": "Either add `def {name}(...):` above line {line} with the steps it needs, or replace the call on line {line} with those steps directly.",
    },
    "undefined_variable": {
        "conceptual_question": "Line {line} reads `{name}`, but no line in your code gives it a value. What should `{name}` hold at this point?",
        "targeted_hint": "Nothing gives `{name}` a value before line {line}. If it is a starting value, it needs its own line above. If it should come from the caller, it needs to be a parameter. Which is it?",
        "name_options": "A name can get its value in only a few ways: an assignment, a parameter, a loop variable, or an import. Which of those should create `{name}` in your code?",
        "step_outline": "1. Decide where the value of `{name}` should come from.\n2. If it is calculated, assign it above line {line}.\n3. If it is passed in, add it to the `def` line.\n4. Check its spelling matches everywhere.\n5. Run your code again.",
        "analogous_example": ("Here is a value created before it is used, on a different task.", "def greeting(name):\n    message = 'Hello ' + name\n    return message", "Where should your `{name}` be created?"),
        "direct_pointer": "Give `{name}` a value on a line above line {line}, or add it as a parameter on your `def` line if it should come from the caller.",
    },
}


class _Blank(dict):
    def __missing__(self, key: str) -> str:
        return "the value"


def name_hint(strategy: str, diagnosis: ErrorDiagnosis, example: str | None) -> str | tuple[str, str, str] | None:
    """The help for this cause and this step. A worked example comes back as (lead, code, closing line)."""
    cause = diagnosis.cause
    table = dict(NAME_HINTS[cause])
    specific = f"{cause}:{diagnosis.variant}" if diagnosis.variant else (f"{cause}:{diagnosis.name}" if f"{cause}:{diagnosis.name}" in NAME_HINTS else None)
    if specific and specific in NAME_HINTS:
        table.update(NAME_HINTS[specific])
    template = table.get(strategy)
    if template is None:
        return None
    defined = diagnosis.defined_at
    values = _Blank(
        name=diagnosis.name or "this name", call=diagnosis.call or diagnosis.name or "this call", line=diagnosis.location if diagnosis.location else "this line", module=diagnosis.module or "the right",
        suggestion=diagnosis.suggestion or "", owner=diagnosis.owner or "value", form=diagnosis.form or "", receiver=diagnosis.receiver or "the value", where=diagnosis.where or "the other function",
        target=diagnosis.target or "the loop variable", defined_at=defined if defined else "another line", purpose=diagnosis.purpose or "this", example=example or "the first example",
        defined_clause=f" on line {defined}" if defined else "",
        first_clause=f"`{diagnosis.name}` first gets a value on line {defined}." if defined else f"`{diagnosis.name}` has no value yet when line {diagnosis.location or 'this'} runs.",
    )
    if isinstance(template, tuple):
        return tuple(part.format_map(values) if index != 1 else part for index, part in enumerate(template))  # type: ignore[return-value]
    return template.format_map(values)


# ---------------------------------------------------------------- other errors

@dataclass(frozen=True)
class Cause:
    key: str
    exception: str
    pattern: str
    likely: str
    concept: str
    question: str
    specific: str
    direct: str
    outline: str | None = None


CAUSES = [
    Cause("mix_text_number", "TypeError", r"can only concatenate str|must be str, not|unsupported operand type\(s\) for \+.*'str'|'str' and '(int|float)'",
          "Text and a number are being joined or added on this line.", "Types: text and numbers",
          "Line {line} combines text with a number. What should the result be: text, or a number?",
          "On line {line}, {source}, one value is text and another is a number, and Python will not guess. If you want text, wrap the number in `str(...)`. If you want a number, wrap the text in `int(...)`. Which do you need?",
          "On line {line}, convert one value so both match: `str(number)` to build text, or `int(text)` to do arithmetic."),
    Cause("not_iterable", "TypeError", r"'(int|float|bool|NoneType)' object is not iterable",
          "A loop or function is being asked to go through a single value, as if it were a collection.", "Loops and what can be looped over",
          "Line {line} tries to go through a value one item at a time, but it is a single {found}. What did you want to go through?",
          "`for` needs a collection, and on line {line} it receives a single {found}. If you want to repeat that many times, what wraps a number to give a run of numbers?",
          "If you want to count up to a number on line {line}, loop over `range(number)`. If you meant a list, check what that variable holds."),
    Cause("not_callable", "TypeError", r"'(\w+)' object is not callable",
          "Brackets after a name call it as a function, but this name holds a plain value. A variable may be reusing a function's name.", "Calling functions and naming variables",
          "On line {line}, brackets after a name mean \"call this\". What does that name hold when this line runs?",
          "Line {line} calls something that holds a {found}, not a function. This often happens when a variable reuses a name like `sum` or `max`. Which name on that line was given a value earlier?",
          "Rename the variable that reuses that function's name, so the name on line {line} still means the function."),
    Cause("none_value", "TypeError", r"'NoneType' object|NoneType",
          "A value here is None. A function with no `return`, or a method like `.sort()`, gives back None.", "Return values and None",
          "A value on line {line} is None. Which function or method produced it, and does that one hand anything back?",
          "Something on line {line} is None. A function without `return` gives None, and so do list methods like `.sort()` and `.append()`. Which line created this value?",
          "Find where that value is created. Use `sorted(items)` instead of storing the result of `.sort()`, or add a `return` to your function."),
    Cause("wrong_arguments", "TypeError", r"required positional argument|positional arguments? but|unexpected keyword argument",
          "A function is being called with a different number of values from what its `def` line lists.", "Function parameters and arguments",
          "Compare the call on line {line} with the function's `def` line. Do they list the same number of values?",
          "Python said: \"{message}\". A call must give one value for each parameter on the `def` line. Which side needs to change?",
          "Make the call on line {line} match the `def` line: one value per parameter, in the same order."),
    Cause("no_len", "TypeError", r"object of type '(\w+)' has no len",
          "`len` is being used on a single value that has no length.", "Types and collections",
          "`len` measures a collection, and line {line} gives it a single {found}. What are you trying to measure?",
          "On line {line}, `len(...)` receives a {found}, which has no length. Should this variable hold a list or text, or do you need the number itself?",
          "On line {line}, either use the number directly, or check where that variable gets its value, so it holds a collection."),
    Cause("bad_index_type", "TypeError", r"indices must be integers",
          "A list position must be a whole number, and this one is something else, such as a loop item or a decimal.", "Lists and indexing",
          "A list position has to be a whole number. What kind of value is inside the square brackets on line {line}?",
          "On line {line}, the value in square brackets is not a whole number. `for x in items` gives you the items themselves, not their positions, and `/` always gives a decimal. Which applies to your code?",
          "If you want the positions, loop over `range(len(items))` or use `enumerate(items)`. If you divided, use `//` for a whole number."),
    Cause("immutable", "TypeError", r"does not support item assignment",
          "This value cannot be changed in place. Text and tuples are fixed once created.", "Mutable and immutable values",
          "Line {line} tries to change one position inside a value. Can text or a tuple be changed in place?",
          "Line {line} assigns to one position, but this value is fixed once created. How could you build a new value instead?",
          "Build a new value: collect the pieces in a list, change the list, then join it back together with `''.join(pieces)`."),
    Cause("unhashable", "TypeError", r"unhashable type",
          "A list or dictionary is being used as a dictionary key or set member, and those must not change.", "Hashing and dictionary keys",
          "Keys of a dictionary and members of a set must never change. What are you using as one on line {line}?",
          "On line {line}, a {found} is used as a key or set member. Lists can change, so Python refuses. What fixed value could stand in for it?",
          "On line {line}, convert the list to a tuple with `tuple(items)` before using it as a key or set member."),
    Cause("bad_compare", "TypeError", r"not supported between instances",
          "Two values of different kinds are being compared with < or >.", "Types and comparisons",
          "Line {line} compares two values with `<` or `>`. What kind of value is each one?",
          "Python said: \"{message}\". Text and numbers cannot be ordered against each other. Which of the two values is not what you expected?",
          "Convert the values on line {line} so both are the same kind, for example with `int(...)`."),
    Cause("none_attribute", "AttributeError", r"'NoneType' object has no attribute",
          "A value here is None, so it has no methods. A function may have reached its end without `return`, or a method like `.sort()` gave back None.", "Return values and None",
          "The value before the dot on line {line} is None. Which line was meant to give it a real value?",
          "On line {line}, the value before the dot is None. Functions with no `return`, and methods like `.sort()` and `.append()`, give back None. Where was this value created?",
          "Find where that value is set. Do not store the result of `.sort()` or `.append()`, and make sure your function ends with `return`."),
    Cause("wrong_method", "AttributeError", r"'(\w+)' object has no attribute '(\w+)'",
          "This method does not exist on this kind of value.", "Methods of each type",
          "A {found} does not have `{attribute}`. What are you trying to do on line {line}?",
          "A {found} has no `.{attribute}` in Python. {suggest_clause} What does your line {line} need?",
          "On line {line}, {suggest_direct}"),
    Cause("pop_empty", "IndexError", r"pop from empty",
          "`.pop()` is being called on an empty list.", "Stacks and lists",
          "Line {line} takes an item from a list that is empty at that moment. Should your code check first?",
          "`.pop()` on line {line} runs when the list is empty. What should your code do when nothing is left to take?",
          "Before line {line}, check the list has items, for example `if items:`, and decide what to do when it is empty."),
    Cause("int_literal", "ValueError", r"invalid literal for int",
          "`int()` received text that is not a whole number.", "Converting text to numbers",
          "`int()` can only read text that is a whole number. What exactly does it receive on line {line}?",
          "Python said: \"{message}\". Check the exact text on line {line}, including empty text, spaces and decimal points. Does it need splitting or cleaning first?",
          "Before `int(...)` on line {line}, clean the text with `.strip()`, or split the line first if it holds more than one number."),
    Cause("empty_min_max", "ValueError", r"(max|min)\(\)|arg is an empty",
          "`max` or `min` is being given an empty collection.", "Edge cases: empty input",
          "`max` and `min` need at least one value. What should your code do when the collection is empty?",
          "On line {line}, `max` or `min` receives an empty collection. What does the task want for empty input?",
          "Before line {line}, check for the empty case, and return what the task asks for."),
    Cause("unpack", "ValueError", r"values to unpack",
          "The number of names on the left does not match the number of values on the right.", "Unpacking values",
          "Line {line} shares out values to several names. How many names are there, and how many values?",
          "Python said: \"{message}\". The count of names on the left of line {line} must match the values on the right. Which side is different?",
          "Make the two sides of line {line} match, one name for each value."),
    Cause("not_in_list", "ValueError", r"is not in list",
          "`.index()` or `.remove()` is looking for a value the list does not contain.", "Searching a list",
          "Line {line} looks for a value in a list. What should happen when it is not there?",
          "`.index()` and `.remove()` raise an error when the value is missing. How could you check first with `in`?",
          "Before line {line}, check `if value in items:`, and handle the case where it is not there."),
]
_METHOD_ALTERNATIVES = {
    ("list", "length"): "use `len(items)`", ("list", "size"): "use `len(items)`", ("list", "add"): "use `.append(value)`", ("list", "push"): "use `.append(value)`", ("list", "contains"): "use `value in items`", ("list", "has"): "use `value in items`",
    ("str", "length"): "use `len(text)`", ("str", "size"): "use `len(text)`", ("str", "append"): "use `text + more`, because text is fixed", ("str", "contains"): "use `part in text`", ("str", "reverse"): "use `text[::-1]`",
    ("dict", "has_key"): "use `key in some_dict`", ("dict", "append"): "assign with `some_dict[key] = value`", ("dict", "add"): "assign with `some_dict[key] = value`", ("set", "append"): "use `.add(value)`",
    ("int", "append"): "check that this variable holds a list", ("int", "length"): "check that this variable holds what you expect",
}
_TYPES = {"list": list, "str": str, "dict": dict, "set": set, "tuple": tuple}
KIND_WORDS = {"int": "whole number", "float": "decimal", "bool": "True or False value", "str": "piece of text", "list": "list", "dict": "dictionary", "set": "set", "tuple": "tuple", "NoneType": "None"}
DEFAULT_RUNTIME = {
    "IndexError": ("A position is being read that does not exist in this sequence.", "Lists and indexing"),
    "KeyError": ("A dictionary key is being read before it has been added.", "Dictionaries"),
    "TypeError": ("An operation received a kind of value it cannot work with.", "Types"),
    "AttributeError": ("This value does not have that method or attribute.", "Methods of each type"),
    "ValueError": ("A function received the right kind of value, with content it cannot use.", "Validating values"),
    "ZeroDivisionError": ("A division has a bottom value of zero for this input.", "Edge cases: division"),
    "RecursionError": ("The function keeps calling itself, and never reaches a stopping case.", "Recursion and base cases"),
    "EOFError": ("The program asks for more lines of input than it was given.", "Reading input"),
}


def analyse_other_error(code: str, error: dict[str, Any], visible: bool) -> ErrorDiagnosis:
    kind = error.get("type") or "Error"
    raw_message = error.get("message") or ""
    line = error.get("line")
    where = f" on line {line}" if line else ""
    error_class = "type" if kind == "TypeError" else "runtime"
    explanation = f"Your code stopped with {kind}{where}."
    for cause in CAUSES:
        if cause.exception == kind and re.search(cause.pattern, raw_message):
            found = re.search(r"'(\w+)'", raw_message)
            attribute = re.search(r"attribute '(\w+)'", raw_message)
            details: dict[str, Any] = {"found": KIND_WORDS.get(found.group(1), found.group(1)) if found else "value", "attribute": attribute.group(1) if attribute else None, "type_name": found.group(1) if found else None}
            if cause.key == "wrong_method" and found and attribute:
                alternative = _METHOD_ALTERNATIVES.get((found.group(1), attribute.group(1)))
                owner = _TYPES.get(found.group(1))
                near = difflib.get_close_matches(attribute.group(1), [m for m in dir(owner) if not m.startswith("_")], n=1, cutoff=0.7) if owner else []
                details["alternative"] = alternative or (f"use `.{near[0]}(...)`" if near else None)
            return ErrorDiagnosis(
                error_class=error_class, cause=cause.key, likely_cause=cause.likely, concept=cause.concept, location=line, evidence=[f"Python reported {kind}{where}."], confidence=0.85, explanation=explanation, details=details,
            )
    likely, concept = DEFAULT_RUNTIME.get(kind, (f"Python raised {kind} here.", "Reading error messages"))
    return ErrorDiagnosis(error_class=error_class, cause=kind, likely_cause=likely, concept=concept, location=line, evidence=[f"Python reported {kind}{where}."], confidence=0.7, explanation=explanation)


CAUSE_INDEX = {cause.key: cause for cause in CAUSES}


def cause_hint(strategy: str, diagnosis: ErrorDiagnosis, evidence_source: str | None, message: str | None) -> str | None:
    cause = CAUSE_INDEX.get(diagnosis.cause)
    if cause is None:
        return None
    template = {"conceptual_question": cause.question, "targeted_hint": cause.specific, "direct_pointer": cause.direct}.get(strategy)
    if template is None:
        return None
    details = diagnosis.details or {}
    alternative = details.get("alternative")
    attribute = details.get("attribute") or "that"
    values = _Blank(
        line=diagnosis.location or "this line", source=f"`{evidence_source}`" if evidence_source else "that line", message=message or diagnosis.likely_cause.rstrip("."), found=details.get("found") or "value", attribute=attribute,
        suggest_clause=f"To do this, {alternative}." if alternative else "Each kind of value has its own methods.", suggest_direct=f"{alternative}." if alternative else "check what kind of value this variable holds, and use a method that kind has.",
    )
    return template.format_map(values)


# ---------------------------------------------------------------- errors that are not exceptions

OTHER_ISSUES = {
    "logic:not_implemented": ("logic", "The function has not been written yet.", "Writing a first version"),
    "logic:missing_return": ("logic", "The result is worked out, but never handed back.", "Return values"),
    "logic:print_instead_of_return": ("logic", "The value is printed rather than returned.", "Return values and printing"),
    "logic:returned_none_on_path": ("logic", "One path through the function ends with no return.", "Return values and branches"),
    "logic:early_return_in_loop": ("logic", "The return runs during the first pass of the loop.", "Loops and return"),
    "logic:off_by_one": ("logic", "A loop or range boundary is one step away from what it should be.", "Loops and boundaries"),
    "logic:edge_case": ("logic", "A case the examples do not show is not handled yet.", "Edge cases"),
    "logic:wrong_return_type": ("logic", "The function gives back a different kind of value from the one asked for.", "Types and return values"),
    "logic:wrong_order": ("logic", "The items are right, in the wrong order.", "Ordering and sorting"),
    "logic:text_format": ("output_mismatch", "The text differs only in spacing or capital letters.", "Exact text output"),
    "logic:stdout_mismatch": ("output_mismatch", "What is printed does not match the expected output exactly.", "Printing exact output"),
    "logic:general": ("logic", "The logic does not match the task yet, and the evidence does not point to one cause.", "Tracing your code"),
    "timeout:loop_no_progress": ("timeout", "This while loop does not change the variables in its condition.", "Loops that end"),
    "timeout:recursion_no_base": ("timeout", "The recursion has no stopping case.", "Recursion and base cases"),
    "timeout:general": ("timeout", "A loop may not end, or the approach may repeat too much work.", "Efficiency and loops that end"),
    "resource:memory": ("timeout", "Something in the code keeps growing.", "Memory use"),
    "resource:output": ("output_mismatch", "A print statement is probably inside a loop that does not end.", "Printing and loops"),
    "structure:missing_function": ("name_resolution", "The function name in your code does not match the one the tests call.", "Defining functions"),
}


def describe_other(category: str, issue_key: str, summary: str, facts: list[str], line: int | None, confidence: float) -> ErrorDiagnosis:
    """Every result gets the same structured diagnosis, built from what was observed."""
    if category == "syntax":
        return ErrorDiagnosis(error_class="syntax", cause=issue_key.split(":")[-1], likely_cause=summary, concept="Python syntax", location=line, evidence=facts[:4], confidence=confidence, explanation=summary)
    error_class, likely, concept = OTHER_ISSUES.get(issue_key, ("logic", summary, "Reading your code"))
    return ErrorDiagnosis(error_class=error_class, cause=issue_key.split(":")[-1], likely_cause=likely, concept=concept, location=line, evidence=facts[:4], confidence=confidence, explanation=summary)
