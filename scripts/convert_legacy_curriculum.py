#!/usr/bin/env python3
"""One-off conversion of the earlier curriculum (branch `lokesh`) into the new content format.

Assert-based test scripts become expression tests, so expected answers live outside the sandbox.
Usage: python scripts/convert_legacy_curriculum.py <legacy_curriculum.json> <legacy_codenet.json>
Output: content/units.json, content/problems/legacy.json
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UNITS = [
    ("python-basics", "Python basics", "foundations", [], ["variables", "data-types"],
     "What a program is, how Python stores values, and how to write your first function."),
    ("variables-io", "Variables, input/output and operators", "foundations", ["python-basics"], ["input-output", "operators"],
     "Reading input, printing output, and doing arithmetic and comparisons."),
    ("conditionals", "Conditionals", "foundations", ["variables-io"], ["if-statements", "if-else", "if-elif-else", "nested-conditions"],
     "Making decisions in code with if, elif and else."),
    ("loops", "Loops", "foundations", ["conditionals"], ["for-loops", "while-loops", "break", "continue"],
     "Repeating work with for and while, and controlling when loops stop."),
    ("functions", "Functions", "foundations", ["loops"], ["functions", "parameters", "return-values", "scope", "lambda-functions", "map", "filter"],
     "Packaging logic into reusable functions, parameters and return values."),
    ("strings", "Strings", "foundations", ["functions"], ["strings", "string-methods", "slicing"],
     "Working with text: indexing, slicing and common methods."),
    ("lists-dicts", "Lists and dictionaries", "foundations", ["functions"], ["lists", "list-methods", "tuples", "sets", "dictionaries", "dictionary-methods", "list-comprehensions", "dictionary-comprehensions"],
     "The everyday collections: lists, tuples, sets and dictionaries."),
    ("recursion", "Recursion", "algorithms", ["functions"], ["recursion", "recursion-problems"],
     "Solving a problem by solving a smaller version of itself."),
    ("searching-sorting", "Searching and sorting", "algorithms", ["lists-dicts"], ["searching", "sorting", "algorithmic-complexity"],
     "Finding and ordering data, and reasoning about how long it takes."),
    ("arrays-two-pointers", "Arrays and two pointers", "dsa", ["lists-dicts"], ["two-pointer"],
     "Walking through arrays with two indices and sliding windows."),
    ("hashing", "Hashing", "dsa", ["lists-dicts"], ["hash-map-problems"],
     "Trading memory for speed with dictionaries and sets."),
    ("stacks-queues", "Stacks and queues", "dsa", ["lists-dicts"], ["stack", "queue"],
     "Last-in first-out and first-in first-out structures."),
    ("linked-lists", "Linked lists", "dsa", ["lists-dicts"], [],
     "Chains of nodes connected by references, and pointer techniques."),
    ("trees", "Trees", "dsa", ["recursion", "linked-lists"], [],
     "Hierarchical data, traversals and binary search trees."),
    ("graphs", "Graphs", "dsa", ["trees", "hashing", "stacks-queues"], [],
     "Networks of nodes, breadth-first and depth-first search."),
    ("dynamic-programming", "Dynamic programming", "dsa", ["recursion", "hashing"], [],
     "Reusing answers to overlapping subproblems."),
    ("python-toolkit", "Python toolkit (optional)", "elective", ["functions"], ["exceptions", "file-handling", "modules", "packages", "classes", "objects", "constructors", "inheritance", "iterators", "generators"],
     "Optional extras: exceptions, modules, classes, iterators and generators."),
]
NEW_LESSONS = {
    "linked-lists": [{"title": "Nodes and references", "explanation": "A linked list stores each value in a node that also holds a reference to the next node. Moving through the list means following those references, so keep track of which node you are on and be careful not to lose the rest of the chain when you change a reference.", "examples": [{"title": "Walking a list", "code": "node = head\nwhile node is not None:\n    print(node.val)\n    node = node.next"}]},
                     {"title": "Fast and slow pointers", "explanation": "Moving one reference two steps for every one step of another finds the middle of a list and detects cycles, using almost no extra memory.", "examples": []}],
    "trees": [{"title": "Binary trees", "explanation": "A binary tree node has a value and up to two children. Most tree problems become simple when you ask what to do at one node, and let recursion handle the subtrees.", "examples": [{"title": "Counting nodes", "code": "def size(node):\n    if node is None:\n        return 0\n    return 1 + size(node.left) + size(node.right)"}]},
              {"title": "Binary search trees", "explanation": "In a binary search tree, smaller values are on the left and larger values are on the right, so each comparison lets you ignore a whole subtree.", "examples": []}],
    "graphs": [{"title": "Representing graphs", "explanation": "An adjacency list maps each node to its neighbours. In Python, a dictionary of lists works well.", "examples": [{"title": "Adjacency list", "code": "graph = {'a': ['b', 'c'], 'b': [], 'c': ['b']}"}]},
               {"title": "Breadth-first and depth-first search", "explanation": "Search visits nodes while remembering which were already seen, so cycles cannot trap you. A queue explores level by level, which gives the fewest steps. A stack or recursion explores deeply.", "examples": []}],
    "dynamic-programming": [{"title": "Overlapping subproblems", "explanation": "If a recursive solution computes the same smaller answer many times, store each answer the first time. That turns exponential work into something practical.", "examples": [{"title": "Memoization", "code": "memo = {}\ndef fib(n):\n    if n < 2:\n        return n\n    if n not in memo:\n        memo[n] = fib(n - 1) + fib(n - 2)\n    return memo[n]"}]},
                            {"title": "Building a table", "explanation": "You can also fill answers from smallest to largest in a list. First define in words what each entry means, then how it depends on earlier entries.", "examples": []}],
    "arrays-two-pointers": [{"title": "Sliding windows", "explanation": "To examine consecutive ranges, update the previous result instead of recomputing it. Add the value entering the window and subtract the one leaving.", "examples": []}],
    "hashing": [{"title": "Why dictionaries are fast", "explanation": "Looking up a key in a dict or set takes about the same time however large it grows. Many nested-loop solutions become single loops by remembering what you have already seen.", "examples": []}],
}
MOVED = {150: "trees", 151: "trees"}
CODENET_UNIT = {201: "loops", 202: "searching-sorting", 203: "strings", 204: "recursion", 205: "loops", 206: "conditionals", 207: "python-toolkit"}


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def tag(value):
    """Encode a Python literal the same way the sandbox encodes results."""
    if isinstance(value, tuple):
        return {"$tuple": [tag(v) for v in value]}
    if isinstance(value, list):
        return [tag(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return {"$set": sorted((tag(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, dict):
        return {"$dict": sorted(([tag(k), tag(v)] for k, v in value.items()), key=lambda x: json.dumps(x[0], sort_keys=True))}
    return value


def script_to_tests(script):
    tree = ast.parse(script)
    setup_lines, tests = [], []

    def add(test_node):
        if isinstance(test_node, ast.BoolOp) and isinstance(test_node.op, ast.And):
            for value in test_node.values:
                add(value)
            return
        setup = "\n".join(setup_lines)
        if isinstance(test_node, ast.Compare) and len(test_node.ops) == 1 and isinstance(test_node.ops[0], (ast.Eq, ast.Is)):
            left = ast.unparse(test_node.left)
            try:
                expected = ast.literal_eval(test_node.comparators[0])
            except ValueError:
                tests.append({"kind": "expr", "setup": setup, "expr": f"bool({ast.unparse(test_node)})", "expected": True})
            else:
                tests.append({"kind": "expr", "setup": setup, "expr": left, "expected": tag(expected)})
            setup_lines.append(left)
        else:
            tests.append({"kind": "expr", "setup": setup, "expr": f"bool({ast.unparse(test_node)})", "expected": True})

    for node in tree.body:
        if isinstance(node, ast.Assert):
            add(node.test)
        else:
            setup_lines.append(ast.unparse(node))
    return tests


def clean_description(text):
    text = text.replace("### Problem Statement\n", "").strip()
    text = re.sub(r"\$O\(([^$]*)\)\$", r"O(\1)", text)
    text = re.sub(r"\$([^$\n]{1,60})\$", r"`\1`", text)
    return text


def convert_problem(p, unit, concepts, source):
    tests = []
    for case in p["test_cases"]:
        if "test_script" in case:
            tests.extend(script_to_tests(case["test_script"]))
        else:
            tests.append({"kind": "args", "args": case["input"], "expected": case["expected"]})
    starter = p["starter_code"].rstrip() + "\n"
    function_name = None
    if any(t["kind"] == "args" for t in tests):
        for node in ast.parse(starter).body:
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                break
    return {
        "slug": slugify(p["title"]), "title": p["title"], "unit": unit, "difficulty": p["difficulty"],
        "concepts": concepts, "description": clean_description(p["description"]),
        "starter_code": starter, "function_name": function_name, "tests": tests,
        "public": min(2, max(1, len(tests) - 1)), "source": source, "legacy_id": p["id"],
    }


def main(curriculum_path, codenet_path):
    concepts = json.loads(Path(curriculum_path).read_text())
    codenet = json.loads(Path(codenet_path).read_text())
    concept_unit = {c: u[0] for u in UNITS for c in u[4]}
    by_id = {c["id"]: c for c in concepts}

    units = []
    for order, (uid, title, track, prereqs, cids, summary) in enumerate(UNITS, start=1):
        lessons = [
            {"title": by_id[c]["title"], "objective": by_id[c].get("learning_objectives", ""),
             "explanation": by_id[c].get("explanation", ""), "examples": by_id[c].get("examples", [])}
            for c in cids if c != "recursion-problems"
        ] + NEW_LESSONS.get(uid, [])
        units.append({"id": uid, "title": title, "order": order, "track": track, "prerequisites": prereqs,
                      "summary": summary, "optional": track == "elective", "lessons": lessons})

    problems = []
    curriculum_source = {"type": "curriculum", "name": "Project curriculum", "note": "Carried over from the project's earlier version."}
    for concept in concepts:
        for p in concept["problems"]:
            unit = MOVED.get(p["id"], concept_unit[concept["id"]])
            problems.append(convert_problem(p, unit, [concept["id"]], curriculum_source))
    for p in codenet:
        source = {
            "type": "codenet_adapted", "name": "Adapted from IBM Project CodeNet catalogue",
            "note": f"Rewritten as a function exercise by the team. Original ID {p.get('codenet_id')}; provenance of the wording not independently verified.",
            "dataset_problem_id": p.get("codenet_id"),
        }
        problems.append(convert_problem(p, CODENET_UNIT[p["id"]], [p.get("concept_id", "general")], source))

    # JSON cannot hold integer or boolean dictionary keys, so these legacy tests could never be passed by correct code.
    for problem in problems:
        if problem["slug"] == "count-frequencies":
            for test in problem["tests"]:
                if test.get("args") == [[1, 1, 1, 1]]:
                    test["expected"] = {"$dict": [[1, 4]]}
                if test.get("args") == [[True, False, True]]:
                    test["expected"] = {"$dict": [[False, 1], [True, 2]]}

    (ROOT / "content/units.json").write_text(json.dumps(units, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "content/problems/legacy.json").write_text(json.dumps(problems, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(units)} units, {len(problems)} problems, {sum(len(p['tests']) for p in problems)} tests")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
