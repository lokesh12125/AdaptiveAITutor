"""A compact way to author practice problems. All wording and solutions here were written for this project.

An example is `(arguments, expected)`, written by hand. A hidden test is just its arguments, and its answer
is worked out from the reference solution when the bank is built. A wrong solution therefore shows up
as a mismatch on the hand-written examples. `scripts/verify_content.py` then checks everything in the sandbox.

A tuple of arguments means several arguments. Anything else means one argument.
"""
from __future__ import annotations

PROBLEMS: list[dict] = []

LIST_PRELUDE = """class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def build_list(values):
    head = None
    for value in reversed(values):
        head = ListNode(value, head)
    return head

def to_list(head, limit=10000):
    out = []
    while head is not None and len(out) < limit:
        out.append(head.val)
        head = head.next
    return out
"""
TREE_PRELUDE = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def build_tree(values):
    \"\"\"Build from level order, where None marks a missing node.\"\"\"
    if not values or values[0] is None:
        return None
    nodes = [None if v is None else TreeNode(v) for v in values]
    children = iter(nodes[1:])
    for node in nodes:
        if node is None:
            continue
        node.left = next(children, None)
        node.right = next(children, None)
    return nodes[0]

def tree_values(root):
    \"\"\"Level order values of a tree, for checking a result.\"\"\"
    if root is None:
        return []
    out, queue = [], [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out
"""


def _add(kind: str, slug: str, title: str, unit: str, difficulty: str, pattern: str, description: str, solution: str, ex: list, hid: list, **extra) -> None:
    PROBLEMS.append({"kind": kind, "slug": slug, "title": title, "unit": unit, "difficulty": difficulty, "pattern": pattern, "description": description.strip(),
                     "solution": solution.strip() + "\n", "ex": list(ex), "hid": list(hid), **extra})


def fn(slug, title, unit, difficulty, pattern, description, solution, ex, hid=(), **extra):
    """A function the tests call directly."""
    _add("fn", slug, title, unit, difficulty, pattern, description, solution, ex, hid, **extra)


def io(slug, title, unit, difficulty, pattern, description, solution, ex, hid=(), **extra):
    """A program that reads standard input and prints. Examples are (stdin, stdout)."""
    _add("io", slug, title, unit, difficulty, pattern, description, solution, ex, hid, **extra)


def exprs(slug, title, unit, difficulty, pattern, description, solution, ex, hid=(), **extra):
    """Tests are Python expressions, for when an argument is itself a function. Examples are (expression, expected)."""
    _add("raw", slug, title, unit, difficulty, pattern, description, solution, ex, hid, **extra)


def linked(slug, title, unit, difficulty, pattern, description, solution, call, ex, hid=(), **extra):
    """`call` is an expression using {0}, {1}. Linked list arguments go through build_list inside `call`."""
    note = "\n\n`ListNode` is already defined for you. Each node has `.val` and `.next`, and an empty list is `None`."
    _add("expr", slug, title, unit, difficulty, pattern, description + note, solution, ex, hid, prelude=LIST_PRELUDE, call=call, **extra)


def tree(slug, title, unit, difficulty, pattern, description, solution, call, ex, hid=(), **extra):
    """`call` is an expression using {0}, {1}. Trees are given in level order, with None for a missing node."""
    note = "\n\n`TreeNode` is already defined for you. Each node has `.val`, `.left` and `.right`, and an empty tree is `None`."
    _add("expr", slug, title, unit, difficulty, pattern, description + note, solution, ex, hid, prelude=TREE_PRELUDE, call=call, **extra)


def klass(slug, title, unit, difficulty, pattern, description, solution, starter, ex, hid=(), **extra):
    """A class or other code the tests use through statements. Examples are (setup, expression, expected), hidden
    tests are (setup, expression). `starter` is the outline the learner starts from."""
    _add("class", slug, title, unit, difficulty, pattern, description, solution, ex, hid, starter=starter, **extra)
