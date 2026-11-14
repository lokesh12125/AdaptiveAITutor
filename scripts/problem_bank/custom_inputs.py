"""Input generators for problems whose rules the examples alone cannot show.

Each generator takes a random.Random and returns one valid input for that problem: a list of arguments for a function,
a list of arguments for a call template (linked lists and trees), a dict with `setup` and `expr` for class and closure
problems, or text for a program that reads input. Every input follows the task's stated rules, such as "exactly one
answer", "sorted", "no loops" or "always reachable". Answers come from the reference solution, in extra_tests.py.
"""
from __future__ import annotations

import random
import string
from collections.abc import Callable
from typing import Any

R = random.Random


# ---------------------------------------------------------------- small helpers

def ints(r: R, n: int, lo: int = -9, hi: int = 9) -> list[int]:
    return [r.randint(lo, hi) for _ in range(n)]


def distinct(r: R, n: int, lo: int = -20, hi: int = 20) -> list[int]:
    return r.sample(range(lo, hi + 1), n)


def word(r: R, lo: int = 1, hi: int = 6, letters: str = "abcde") -> str:
    return "".join(r.choice(letters) for _ in range(r.randint(lo, hi)))


def sentence(r: R, lo: int = 0, hi: int = 5, letters: str = "abcdefg") -> str:
    return " ".join(word(r, 1, 6, letters) for _ in range(r.randint(lo, hi)))


def grid(r: R, rows: int, cols: int, values: tuple = (0, 1), weights: tuple | None = None) -> list[list[int]]:
    return [[r.choices(values, weights)[0] for _ in range(cols)] for _ in range(rows)]


class Node:
    def __init__(self, val: int) -> None:
        self.val, self.left, self.right = val, None, None


def level_order(root: Node | None) -> list[Any]:
    out: list[Any] = []
    queue = [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue += [node.left, node.right]
    while out and out[-1] is None:
        out.pop()
    return out


def random_tree(r: R, size: int, lo: int = -9, hi: int = 20) -> list[Any]:
    if size == 0:
        return []
    root = Node(r.randint(lo, hi))
    nodes = [root]
    for _ in range(size - 1):
        while True:
            parent = r.choice(nodes)
            side = r.choice(("left", "right"))
            if getattr(parent, side) is None:
                child = Node(r.randint(lo, hi))
                setattr(parent, side, child)
                nodes.append(child)
                break
    return level_order(root)


def bst(r: R, size: int, lo: int = 1, hi: int = 40) -> tuple[list[Any], list[int]]:
    values = r.sample(range(lo, hi + 1), size)
    root = None
    for value in values:
        node = Node(value)
        if root is None:
            root = node
            continue
        cur = root
        while True:
            side = "left" if value < cur.val else "right"
            if getattr(cur, side) is None:
                setattr(cur, side, node)
                break
            cur = getattr(cur, side)
    return level_order(root), values


def mirror_tree(r: R, size: int) -> list[Any]:
    def build(depth: int) -> Node | None:
        if depth == 0 or r.random() < 0.25:
            return None
        node = Node(r.randint(1, 5))
        node.left, node.right = build(depth - 1), build(depth - 1)
        return node

    def mirror(node: Node | None) -> Node | None:
        if node is None:
            return None
        copy = Node(node.val)
        copy.left, copy.right = mirror(node.right), mirror(node.left)
        return copy

    root = Node(r.randint(1, 5))
    root.left = build(max(1, size // 3))
    root.right = mirror(root.left)
    return level_order(root)


def dag_rules(r: R, n: int, count: int) -> list[list[int]]:
    """Pairs [a, b] meaning b comes before a, with b < a so there is never a loop."""
    pairs = {(a, b) for a in range(n) for b in range(a) if a != b}
    chosen = r.sample(sorted(pairs), min(count, len(pairs)))
    return [[a, b] for a, b in chosen]


def undirected_edges(r: R, n: int, count: int) -> list[list[int]]:
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    return [list(p) for p in r.sample(pairs, min(count, len(pairs)))]


def adjacency(r: R, n: int, p: float = 0.35, dag: bool = False) -> list[list[int]]:
    return [[j for j in range(n) if j != i and (not dag or j > i) and r.random() < p] for i in range(n)]


def rpn(r: R, depth: int) -> list[str]:
    if depth == 0 or r.random() < 0.3:
        return [str(r.randint(1, 12))]
    return rpn(r, depth - 1) + rpn(r, depth - 1) + [r.choice("+-*")]


def calc_expr(r: R, depth: int) -> str:
    if depth == 0 or r.random() < 0.35:
        return str(r.randint(0, 30))
    left, right = calc_expr(r, depth - 1), calc_expr(r, depth - 1)
    text = f"{left} {r.choice('+-')} {right}"
    return f"({text})" if r.random() < 0.5 else text


def encoded(r: R, depth: int) -> str:
    parts = []
    for _ in range(r.randint(1, 3)):
        if depth > 0 and r.random() < 0.5:
            parts.append(f"{r.randint(1, 3)}[{encoded(r, depth - 1)}]")
        else:
            parts.append(word(r, 1, 3, "abc"))
    return "".join(parts)


def unique_pair(r: R, sorted_input: bool) -> tuple[list[int], int, bool]:
    """A list with exactly one pair adding up to the target, or none."""
    while True:
        nums = distinct(r, r.randint(2, 9), -15, 25)
        if sorted_input:
            nums.sort()
        if r.random() < 0.2:
            target = r.randint(-30, 50)
        else:
            i, j = sorted(r.sample(range(len(nums)), 2))
            target = nums[i] + nums[j]
        pairs = [(a, b) for a in range(len(nums)) for b in range(a + 1, len(nums)) if nums[a] + nums[b] == target]
        if len(pairs) <= 1:
            return nums, target, bool(pairs)


def rotated(r: R) -> list[int]:
    nums = sorted(distinct(r, r.randint(1, 10), -10, 30))
    k = r.randrange(len(nums))
    return nums[k:] + nums[:k]


def reachable_jumps(r: R) -> list[int]:
    while True:
        nums = [r.randint(0, 3) for _ in range(r.randint(1, 9))]
        far = 0
        for i, step in enumerate(nums):
            if i > far:
                break
            far = max(far, i + step)
        if far >= len(nums) - 1:
            return nums


def browse_ops(r: R) -> list[list[str]]:
    ops = []
    for _ in range(r.randint(0, 8)):
        kind = r.choice(("visit", "visit", "back", "forward"))
        ops.append([kind, word(r, 1, 3, "xyz")] if kind == "visit" else [kind])
    return ops


def stack_ops(r: R, with_min: bool) -> list[list[Any]]:
    ops: list[list[Any]] = []
    size = 0
    for _ in range(r.randint(0, 10)):
        choices = ["push", "push"] + (["pop"] if size or not with_min else []) + (["min"] if with_min and size else [])
        kind = r.choice(choices)
        if kind == "push":
            ops.append(["push", r.randint(-9, 9)])
            size += 1
        else:
            ops.append([kind])
            size -= 1 if kind == "pop" and size else 0
    return ops


def ladder_input(r: R) -> list[Any]:
    letters = "abc"
    words = sorted({word(r, 3, 3, letters) for _ in range(r.randint(2, 10))})
    start = word(r, 3, 3, letters)
    end = r.choice(words) if r.random() < 0.8 else word(r, 3, 3, letters)
    return [start, end, words]


def pattern_input(r: R) -> list[str]:
    pattern = word(r, 1, 5, "ab")
    words = {letter: word(r, 1, 4, "xyz") for letter in "ab"}
    text = " ".join(words[c] for c in pattern)
    if r.random() < 0.4:
        parts = text.split()
        parts[r.randrange(len(parts))] = word(r, 1, 4, "xyz")
        text = " ".join(parts)
    return [pattern, text]


def nested(r: R, depth: int) -> list[Any]:
    return [nested(r, depth - 1) if depth and r.random() < 0.35 else r.randint(0, 9) for _ in range(r.randint(0, 4))]


def path_text(r: R) -> str:
    parts = [r.choice(["a", "b", "c", ".", "..", ""]) for _ in range(r.randint(0, 6))]
    return "/" + "/".join(parts) + r.choice(["", "/"])


def islands_text(r: R) -> list[str]:
    rows, cols = r.randint(1, 5), r.randint(1, 5)
    return ["".join(r.choice("01") for _ in range(cols)) for _ in range(rows)]


def town(r: R) -> list[Any]:
    n = r.randint(1, 5)
    trust = {(a, b) for a in range(1, n + 1) for b in range(1, n + 1) if a != b and r.random() < 0.3}
    if n > 1 and r.random() < 0.6:
        judge = r.randint(1, n)
        trust = {(a, b) for a, b in trust if a != judge} | {(a, judge) for a in range(1, n + 1) if a != judge}
    return [n, [list(p) for p in sorted(trust)]]


def weighted(r: R) -> list[Any]:
    n = r.randint(2, 6)
    edges = [[a, b, r.randint(0, 9)] for a in range(n) for b in range(n) if a != b and r.random() < 0.3]
    return [n, edges, 0, n - 1]


def ranges(r: R) -> list[list[int]]:
    out = []
    for _ in range(r.randint(0, 6)):
        start = r.randint(0, 20)
        out.append([start, start + r.randint(0, 6)])
    return out


def queries(r: R) -> list[Any]:
    nums = ints(r, r.randint(1, 8))
    qs = []
    for _ in range(r.randint(0, 5)):
        i = r.randrange(len(nums))
        qs.append([i, r.randint(i, len(nums) - 1)])
    return [nums, qs]


def students(r: R) -> list[Any]:
    names = r.sample(list("abcdefgh"), r.randint(0, 6))
    return [[[name, r.randint(0, 5)] for name in names], r.randint(0, len(names) + 1)]


def missing(r: R) -> list[list[int]]:
    n = r.randint(1, 10)
    nums = list(range(n + 1))
    nums.remove(r.choice(nums))
    r.shuffle(nums)
    return [nums]


def letter_value(r: R) -> list[Any]:
    return [r.choice([3, -2, 0, 4.5, "word", "", True, None, [1, 2], (1,), {"a": 1}, {1, 2}, 2.0])]


def list_k(r: R, lo: int = 1) -> list[Any]:
    nums = ints(r, r.randint(1, 8))
    return [nums, r.randint(lo, len(nums))]


# ---------------------------------------------------------------- generators by problem

GENERATORS: dict[str, Callable[[R], Any]] = {
    # functions with plain values
    "variable-swap": lambda r: [r.choice([r.randint(-50, 50), word(r)]), r.choice([r.randint(-50, 50), word(r)])],
    "type-converter": lambda r: [str(r.randint(-500, 500)), str(r.randint(-500, 500))],
    "first-negative": lambda r: [ints(r, r.randint(0, 8), -9, 15)],
    "power-with-default": lambda r: [r.randint(-6, 9)] if r.random() < 0.5 else [r.randint(-6, 9), r.randint(0, 5)],
    "count-frequencies": lambda r: [[r.choice("abcd") for _ in range(r.randint(0, 8))]],
    "every-second-element": lambda r: [ints(r, r.randint(0, 9), 0, 99)],
    "safe-divide": lambda r: [r.randint(-100, 100), r.choice([0, r.randint(1, 12), -r.randint(1, 12)])],
    "count-lines-from-text": lambda r: ["\n".join(r.choice(["hello", "", "  ", "x y", "\t"]) for _ in range(r.randint(1, 6)))],
    "normalize-module-name": lambda r: ["/".join(word(r, 1, 6, "abcdefg") for _ in range(r.randint(1, 4))) + ".py"],
    "binary-search": lambda r: (lambda nums: [nums, r.choice(nums) if nums and r.random() < 0.7 else r.randint(-25, 25)])(sorted(distinct(r, r.randint(0, 10)))),
    "two-sum-fast": lambda r: (lambda u: [u[0], u[1]])(unique_pair(r, False)),
    "valid-parentheses": lambda r: ["".join(r.choice("()[]{}") for _ in range(r.randint(0, 10)))],
    "recent-counter-queue-processor": lambda r: [[f"job{i}" for i in range(1, r.randint(0, 7) + 1)]],
    "identify-duplicate-o-n": lambda r: [ints(r, r.randint(0, 9), 0, 9)],
    "pair-with-target-sum": lambda r: (lambda u: [u[0], u[1]])(unique_pair(r, True)),
    "max-window-sum": lambda r: [ints(r, r.randint(0, 8)), r.randint(1, 5)],
    "first-unique-character": lambda r: [word(r, 0, 10, "abcd")],
    "group-anagrams": lambda r: [[r.choice(["eat", "tea", "ate", "tan", "nat", "bat", "tab", "cat", "act", "dog"]) for _ in range(r.randint(0, 7))]],
    "longest-consecutive-run": lambda r: [ints(r, r.randint(0, 10), -5, 15)],
    "evaluate-rpn": lambda r: [rpn(r, 3)],
    "next-warmer-day": lambda r: [ints(r, r.randint(0, 9), 60, 80)],
    "graph-has-path": lambda r: (lambda g: [g, r.choice(list(g)), r.choice(list(g))])({c: r.sample("abcde", r.randint(0, 3)) for c in "abcde"}),
    "bfs-shortest-steps": lambda r: (lambda g: [g, r.choice(list(g)), r.choice(list(g))])({c: r.sample("abcdef", r.randint(0, 2)) for c in "abcdef"}),
    "count-islands": lambda r: [islands_text(r)],
    "course-order-possible": lambda r: (lambda n: [n, [[r.randrange(n), r.randrange(n)] for _ in range(r.randint(0, n + 1))] if r.random() < 0.4 else dag_rules(r, n, r.randint(0, n + 1))])(r.randint(1, 5)),
    "climbing-stairs": lambda r: [r.randint(0, 25)],
    "house-robber": lambda r: [ints(r, r.randint(0, 9), 0, 20)],
    "describe-type-name": letter_value,
    "vowel-or-consonant": lambda r: [r.choice(string.ascii_letters)],
    "point-quadrant": lambda r: [r.choice([0, r.randint(-9, 9)]), r.choice([0, r.randint(-9, 9)])],
    "rock-paper-scissors": lambda r: [r.choice(["rock", "paper", "scissors"]), r.choice(["rock", "paper", "scissors"])],
    "password-strength-basic": lambda r: ["".join(r.choice("abcXY123") for _ in range(r.randint(0, 12)))],
    "multiplication-grid": lambda r: [r.randint(0, 6)],
    "first-and-last-pair": lambda r: [ints(r, r.randint(1, 7), 0, 50)],
    "greeting-with-default": lambda r: [word(r, 1, 6, "AdaLinusGrace").capitalize()] if r.random() < 0.5 else [word(r, 1, 6).capitalize(), r.choice(["Hi", "Welcome", "Hey"])],
    "sum-any-number-of-values": lambda r: ints(r, r.randint(0, 6), -20, 20),
    "largest-by-length": lambda r: [[word(r, 1, 6) for _ in range(r.randint(0, 6))]],
    "count-vowels": lambda r: [word(r, 0, 12, "aeiouAEIbcdXY ")],
    "most-common-letter": lambda r: [word(r, 1, 10, "abcd")],
    "capitalise-each-word": lambda r: [" ".join(word(r, 1, 6, "abcABC") for _ in range(r.randint(1, 4)))],
    "remove-vowels": lambda r: [word(r, 0, 12, "aeiouAEbcdXY ")],
    "are-anagrams": lambda r: (lambda a: [a, "".join(r.sample(a, len(a))).upper() if r.random() < 0.5 else word(r, 0, 6, "abcd")])(word(r, 0, 6, "abcd")),
    "longest-word-in-sentence": lambda r: [sentence(r)],
    "second-largest-value": lambda r: [ints(r, r.randint(0, 7), 0, 9)],
    "flatten-one-level": lambda r: [[ints(r, r.randint(0, 3), 0, 9) for _ in range(r.randint(0, 4))]],
    "matrix-row-sums": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), tuple(range(-5, 10)))],
    "transpose-a-matrix": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), tuple(range(0, 10)))],
    "diagonal-sum": lambda r: (lambda n: [grid(r, n, n, tuple(range(-5, 10)))])(r.randint(1, 5)),
    "spiral-matrix-order": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), tuple(range(1, 20)))],
    "merge-two-dictionaries": lambda r: [{k: r.randint(0, 9) for k in r.sample("wxyz", r.randint(0, 3))}, {k: r.randint(0, 9) for k in r.sample("wxyz", r.randint(0, 3))}],
    "get-with-a-default": lambda r: [{k: r.randint(1, 9) for k in r.sample(["tea", "jam", "bun", "egg"], r.randint(0, 3))}, r.choice(["tea", "jam", "bun", "egg"])],
    "total-prices": lambda r: [{k: r.randint(1, 9) for k in r.sample(["tea", "jam", "bun"], r.randint(0, 3))}, [r.choice(["tea", "jam", "bun", "egg"]) for _ in range(r.randint(0, 5))]],
    "key-with-largest-value": lambda r: [{k: r.randint(0, 4) for k in r.sample("abcde", r.randint(0, 4))}],
    "flatten-any-depth": lambda r: [nested(r, 3)],
    "all-subsets": lambda r: [sorted(distinct(r, r.randint(0, 4), 0, 9))],
    "all-permutations": lambda r: [sorted(distinct(r, r.randint(0, 4), 0, 9))],
    "generate-balanced-brackets": lambda r: [r.randint(1, 5)],
    "n-queens-count": lambda r: [r.randint(1, 7)],
    "linear-search-index": lambda r: [ints(r, r.randint(0, 8), 0, 5), r.randint(0, 6)],
    "first-position-sorted": lambda r: [sorted(ints(r, r.randint(0, 9), 0, 6)), r.randint(-1, 7)],
    "last-position-sorted": lambda r: [sorted(ints(r, r.randint(0, 9), 0, 6)), r.randint(-1, 7)],
    "search-rotated-list": lambda r: (lambda nums: [nums, r.choice(nums) if r.random() < 0.7 else r.randint(-12, 32)])(rotated(r)),
    "rotation-minimum": lambda r: [rotated(r)],
    "sort-by-absolute-value": lambda r: [ints(r, r.randint(0, 8))],
    "top-k-students": students,
    "merge-overlapping-ranges": lambda r: [ranges(r)],
    "kth-largest-value": list_k,
    "unique-count-sorted": lambda r: [sorted(ints(r, r.randint(0, 9), 0, 6))],
    "flip-zeros-longest-ones": lambda r: [ints(r, r.randint(0, 10), 0, 1), r.randint(0, 3)],
    "range-sum-queries": queries,
    "has-duplicate-value": lambda r: [ints(r, r.randint(0, 8), 0, 9)],
    "first-repeated-value": lambda r: [ints(r, r.randint(0, 8), 0, 6)],
    "missing-number-in-range": missing,
    "most-frequent-value": lambda r: [ints(r, r.randint(1, 9), 0, 5)],
    "top-k-frequent-values": lambda r: (lambda nums: [nums, r.randint(1, len(set(nums)))])(ints(r, r.randint(1, 10), 0, 5)),
    "majority-value-check": lambda r: [ints(r, r.randint(0, 9), 0, 2)],
    "word-pattern-match": pattern_input,
    "reverse-with-a-stack": lambda r: [ints(r, r.randint(0, 7), 0, 9)],
    "min-stack-operations": lambda r: [stack_ops(r, True)],
    "simplify-file-path": lambda r: [path_text(r)],
    "longest-balanced-brackets": lambda r: [word(r, 0, 12, "()")],
    "decode-repeat-string": lambda r: [encoded(r, 2)],
    "basic-calculator-plus-minus": lambda r: [calc_expr(r, 3)],
    "queue-simulation-order": lambda r: [[r.choice(["ann", "bo", "cy", "next", "next"]) for _ in range(r.randint(0, 8))]],
    "round-robin-last": lambda r: [r.randint(1, 10), r.randint(1, 5)],
    "stack-from-a-queue": lambda r: [stack_ops(r, False)],
    "browser-history-steps": lambda r: [word(r, 1, 3, "xyz"), browse_ops(r)],
    "neighbours-from-edges": lambda r: (lambda n: [n, undirected_edges(r, n, r.randint(0, n + 2))])(r.randint(1, 6)),
    "node-degrees": lambda r: (lambda n: [n, undirected_edges(r, n, r.randint(0, n + 2))])(r.randint(1, 6)),
    "find-town-judge": town,
    "bfs-visit-order": lambda r: [adjacency(r, r.randint(1, 6)), 0],
    "distance-to-every-node": lambda r: [adjacency(r, r.randint(1, 6)), 0],
    "word-ladder-steps": ladder_input,
    "count-components": lambda r: (lambda n: [n, undirected_edges(r, n, r.randint(0, n))])(r.randint(1, 7)),
    "dfs-visit-order": lambda r: [adjacency(r, r.randint(1, 6)), 0],
    "undirected-cycle-check": lambda r: (lambda n: [n, undirected_edges(r, n, r.randint(0, n + 1))])(r.randint(1, 6)),
    "bipartite-check": lambda r: (lambda edges, n: [[sorted({b for a, b in edges if a == i} | {a for a, b in edges if b == i}) for i in range(n)]])(*(lambda n: (undirected_edges(r, n, r.randint(0, n + 1)), n))(r.randint(1, 6))),
    "all-paths-in-dag": lambda r: [adjacency(r, r.randint(2, 6), 0.45, dag=True)],
    "largest-island-area": lambda r: [grid(r, r.randint(1, 5), r.randint(1, 5))],
    "flood-fill-grid": lambda r: (lambda g: [g, r.randrange(len(g)), r.randrange(len(g[0])), r.randint(0, 3)])(grid(r, r.randint(1, 4), r.randint(1, 4), (0, 1, 2))),
    "shortest-path-in-maze": lambda r: [grid(r, r.randint(1, 5), r.randint(1, 5), (0, 1), (3, 1))],
    "rotting-spread-minutes": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), (0, 1, 2), (1, 3, 1))],
    "course-order-list": lambda r: (lambda n: [n, dag_rules(r, n, r.randint(0, n + 1))])(r.randint(1, 6)),
    "dag-longest-path": lambda r: (lambda n: [n, dag_rules(r, n, r.randint(0, n + 2))])(r.randint(1, 6)),
    "cheapest-path-weighted": weighted,
    "grid-paths-memo": lambda r: [r.randint(1, 7), r.randint(1, 7)],
    "grid-paths-with-walls": lambda r: [grid(r, r.randint(1, 5), r.randint(1, 5), (0, 1), (4, 1))],
    "cheapest-grid-path": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), tuple(range(0, 10)))],
    "max-square-of-ones": lambda r: [grid(r, r.randint(1, 5), r.randint(1, 5), (0, 1), (1, 3))],
    "min-cost-stairs": lambda r: [ints(r, r.randint(2, 9), 0, 20)],
    "longest-palindromic-part": lambda r: [word(r, 1, 10, "abc")],
    "min-jumps-to-end": lambda r: [reachable_jumps(r)],
    # linked lists and trees: arguments for the call template
    "linked-list-length": lambda r: [ints(r, r.randint(0, 9))],
    "linked-list-sum": lambda r: [ints(r, r.randint(0, 9))],
    "linked-list-contains": lambda r: [ints(r, r.randint(0, 7), 0, 9), r.randint(0, 9)],
    "linked-list-kth-from-end": list_k,
    "delete-all-of-value": lambda r: [ints(r, r.randint(0, 8), 0, 3), r.randint(0, 3)],
    "remove-kth-from-end": list_k,
    "dedupe-sorted-linked-list": lambda r: [sorted(ints(r, r.randint(0, 9), 0, 5))],
    "swap-adjacent-nodes": lambda r: [ints(r, r.randint(0, 8), 0, 9)],
    "reverse-part-of-list": lambda r: (lambda nums: (lambda a: [nums, a, r.randint(a, len(nums))])(r.randint(1, len(nums))))(ints(r, r.randint(1, 8), 0, 9)),
    "rotate-linked-list": lambda r: [ints(r, r.randint(0, 7), 0, 9), r.randint(0, 10)],
    "linked-list-palindrome": lambda r: (lambda half: [half + half[::-1][r.randint(0, 1):]] if r.random() < 0.5 else [ints(r, r.randint(0, 6), 0, 3)])(ints(r, r.randint(0, 4), 0, 3)),
    "odd-positions-first": lambda r: [ints(r, r.randint(0, 8), 0, 9)],
    "partition-around-value": lambda r: [ints(r, r.randint(0, 8), 0, 9), r.randint(0, 9)],
    "add-numbers-as-lists": lambda r: [[r.randint(0, 9) for _ in range(r.randint(1, 5))], [r.randint(0, 9) for _ in range(r.randint(1, 5))]],
    "reorder-ends-alternating": lambda r: [ints(r, r.randint(0, 8), 0, 9)],
    "count-tree-nodes": lambda r: [random_tree(r, r.randint(0, 9))],
    "tree-value-total": lambda r: [random_tree(r, r.randint(0, 9))],
    "preorder-values": lambda r: [random_tree(r, r.randint(0, 9))],
    "postorder-values": lambda r: [random_tree(r, r.randint(0, 9))],
    "count-tree-leaves": lambda r: [random_tree(r, r.randint(0, 9))],
    "level-averages": lambda r: [random_tree(r, r.randint(1, 9))],
    "right-side-view": lambda r: [random_tree(r, r.randint(0, 9))],
    "zigzag-levels": lambda r: [random_tree(r, r.randint(0, 9))],
    "same-tree-check": lambda r: (lambda t: [t, list(t) if r.random() < 0.5 else random_tree(r, len([v for v in t if v is not None]))])(random_tree(r, r.randint(0, 6))),
    "symmetric-tree-check": lambda r: [mirror_tree(r, r.randint(1, 9))] if r.random() < 0.6 else [random_tree(r, r.randint(0, 7), 1, 5)],
    "balanced-tree-check": lambda r: [random_tree(r, r.randint(0, 9))],
    "tree-diameter": lambda r: [random_tree(r, r.randint(1, 10))],
    "insert-into-bst": lambda r: (lambda t: [t[0], r.choice([v for v in range(1, 50) if v not in t[1]])])(bst(r, r.randint(1, 8))),
    "validate-bst": lambda r: [bst(r, r.randint(1, 8))[0]] if r.random() < 0.5 else [random_tree(r, r.randint(1, 7), 1, 20)],
    "smallest-kth-in-bst": lambda r: (lambda t: [t[0], r.randint(1, len(t[1]))])(bst(r, r.randint(1, 8))),
    "root-to-leaf-sum": lambda r: [random_tree(r, r.randint(0, 8), -3, 9), r.randint(-3, 25)],
    "all-root-to-leaf-paths": lambda r: [random_tree(r, r.randint(0, 8), 0, 9)],
    "lowest-common-ancestor-bst": lambda r: (lambda t: (lambda pair: [t[0], pair[0], pair[1]])(r.sample(t[1], 2) if len(t[1]) > 1 else [t[1][0], t[1][0]]))(bst(r, r.randint(2, 8))),
    # programs that read input
    "add-two-numbers-input": lambda r: f"{r.randint(-99, 99)}\n{r.randint(-99, 99)}\n",
    "echo-a-word": lambda r: word(r, 1, 8, "abcdeXYZ") + "\n",
    "greet-by-name": lambda r: r.choice(["Ada", "Linus", "Grace", "Tim", "Mo", "Priya", "Kenji", "Sofia", "Omar", "Lena", "Ravi", "Zoe", "Ali", "Mei", "Noah"]) + "\n",
    "sum-of-three-lines": lambda r: "".join(f"{r.randint(-50, 50)}\n" for _ in range(3)),
    "numbers-on-one-line": lambda r: f"{r.randint(-20, 20)} {r.randint(-20, 20)}\n",
    "rectangle-from-input": lambda r: f"{r.randint(1, 30)}\n{r.randint(1, 30)}\n",
    "swap-the-order": lambda r: f"{word(r)}\n{word(r)}\n",
    "split-the-bill": lambda r: f"{r.randint(1, 500)}\n{r.randint(1, 9)}\n",
}

# Classes, closures and iterators, written by hand: (setup, expression)
HANDWRITTEN: dict[str, list[tuple[str, str]]] = {
    "invert-dictionary": [("", "invert_dict({'x': 10, 'y': 20, 'z': 30})"), ("", "invert_dict({1: 'one'})"), ("", "invert_dict({'a': (1, 2)})"), ("", "invert_dict({'k': 'v', 'v': 'k'})"), ("", "invert_dict({True: 0})"), ("", "invert_dict({'p': -1, 'q': -2})"), ("", "len(invert_dict({i: i * 2 for i in range(9)}))"), ("", "invert_dict({'a': None})")],
    "multiplier-factory": [("f = make_multiplier(-2)", "f(7)"), ("f = make_multiplier(0)", "f(99)"), ("f = make_multiplier(2.5)", "f(4)"), ("f = make_multiplier(1)", "f(-3)"), ("a = make_multiplier(2); b = make_multiplier(10)", "a(3) + b(3)"), ("f = make_multiplier(3)", "[f(i) for i in range(4)]"), ("f = make_multiplier(-1)", "f(-8)")],
    "sort-tuples-by-second-item": [("", "sort_by_second([(1, 9), (2, 8), (3, 7)])"), ("", "sort_by_second([('a', 2), ('b', 2), ('c', 1)])"), ("", "sort_by_second([(5, -1)])"), ("", "sort_by_second([(1, 0.5), (2, 0.25)])"), ("", "sort_by_second([(0, 3), (1, 3), (2, 3)])"), ("", "sort_by_second([('x', 10), ('y', -10), ('z', 0)])"), ("", "sort_by_second([(i, 5 - i) for i in range(6)])")],
    "counter-class": [("c = Counter(); c.increment(); c.increment()", "c.get_count()"), ("c = Counter(); c.increment(5)", "c.get_count()"), ("c = Counter(); c.increment(3); c.increment(-1)", "c.get_count()"), ("a = Counter(); b = Counter(); a.increment()", "b.get_count()"), ("c = Counter()\nfor _ in range(10):\n    c.increment(2)", "c.get_count()"), ("c = Counter(); c.increment(0)", "c.get_count()"), ("c = Counter(); c.increment(); c.increment(step=4)", "c.get_count()")],
    "point-class": [("p = Point(0, 0); p.move(3, 4)", "(p.x, p.y)"), ("p = Point(-2, 5); p.move(2, -5)", "(p.x, p.y)"), ("p = Point(1, 1); p.move(1, 1); p.move(1, 1)", "(p.x, p.y)"), ("a = Point(1, 2); b = Point(3, 4); a.move(10, 10)", "(b.x, b.y)"), ("p = Point(1.5, 2.5); p.move(0.5, 0.5)", "(p.x, p.y)"), ("p = Point(7, 8)", "p.x + p.y")],
    "rectangle-area": [("r = Rectangle(1, 1)", "r.area()"), ("r = Rectangle(0, 9)", "r.area()"), ("r = Rectangle(2.5, 4)", "r.area()"), ("r = Rectangle(12, 3)", "r.area()"), ("a = Rectangle(2, 3); b = Rectangle(4, 5)", "a.area() + b.area()"), ("r = Rectangle(100, 100)", "r.area()"), ("r = Rectangle(7, 1)", "r.area()"), ("r = Rectangle(3, 3)", "r.area()"), ("r = Rectangle(6, 9)", "r.area()")],
    "square-inherits-rectangle": [("s = Square(1)", "s.area()"), ("s = Square(0)", "s.area()"), ("s = Square(2.5)", "s.area()"), ("s = Square(12)", "s.area()"), ("s = Square(3)", "isinstance(s, Rectangle)"), ("s = Square(4)", "s.area() == Rectangle(4, 4).area()"), ("s = Square(9)", "s.area()"), ("s = Square(7)", "s.area()")],
    "custom-range-iterator": [("", "list(RangeIterator(0, 5))"), ("", "list(RangeIterator(-3, 0))"), ("", "list(RangeIterator(4, 2))"), ("", "list(RangeIterator(7, 8))"), ("it = RangeIterator(1, 3); next(it)", "next(it)"), ("", "sum(RangeIterator(1, 11))"), ("", "[x * 2 for x in RangeIterator(0, 4)]"), ("", "list(RangeIterator(10, 13))"), ("", "len(list(RangeIterator(0, 9)))")],
    "even-number-generator": [("", "list(even_generator(1))"), ("", "list(even_generator(7))"), ("", "list(even_generator(10))"), ("", "sum(even_generator(20))"), ("g = even_generator(4); next(g)", "next(g)"), ("", "len(list(even_generator(99)))"), ("", "list(even_generator(2))"), ("", "list(even_generator(3))")],
    "bank-account-class": [("a = BankAccount('Bo')", "a.get_balance()"), ("a = BankAccount('Bo', 10)", "a.withdraw(20)"), ("a = BankAccount('Bo', 10); a.withdraw(20)", "a.get_balance()"), ("a = BankAccount('Bo', 10)", "a.withdraw(10)"), ("a = BankAccount('Bo', 10); a.deposit(-5)", "a.get_balance()"), ("a = BankAccount('Bo', 10); a.deposit(5); a.withdraw(3)", "a.get_balance()"), ("a = BankAccount('Cy', 5)", "a.withdraw(0)"), ("a = BankAccount('Cy', 5)", "a.owner")],
    "queue-from-two-stacks": [("q = StackQueue(); q.push(1); q.push(2); q.push(3); q.pop()", "q.pop()"), ("q = StackQueue(); q.push(1); q.pop(); q.push(2)", "q.pop()"), ("q = StackQueue(); q.push(5)", "q.size()"), ("q = StackQueue(); q.push(1); q.push(2); q.pop(); q.push(3)", "[q.pop(), q.pop(), q.pop()]"), ("q = StackQueue()", "q.size()"), ("q = StackQueue()\nfor i in range(5):\n    q.push(i)", "[q.pop() for _ in range(5)]"), ("q = StackQueue(); q.push(9); q.pop()", "q.size()")],
    "reverse-linked-list": [("h = build_list([])", "to_list(reverse_list(h))"), ("h = build_list([7])", "to_list(reverse_list(h))"), ("h = build_list([1, 2])", "to_list(reverse_list(h))"), ("h = build_list([5, 4, 3, 2, 1])", "to_list(reverse_list(h))"), ("h = build_list([1, 1, 2, 2])", "to_list(reverse_list(h))"), ("h = build_list(list(range(10)))", "to_list(reverse_list(h))"), ("h = build_list([-3, 0, 3])", "to_list(reverse_list(h))"), ("h = build_list([9, 8])", "to_list(reverse_list(h))")],
    "middle-of-linked-list": [("h = build_list([1])", "middle_node(h).val"), ("h = build_list([1, 2])", "middle_node(h).val"), ("h = build_list([1, 2, 3])", "middle_node(h).val"), ("h = build_list(list(range(10)))", "middle_node(h).val"), ("h = build_list([4, 5, 6, 7, 8, 9, 10])", "middle_node(h).val"), ("h = build_list([2, 4, 6, 8])", "to_list(middle_node(h))"), ("h = build_list([9, 9, 9])", "middle_node(h).val")],
    "merge-two-linked-lists": [("a = build_list([]); b = build_list([])", "to_list(merge_lists(a, b))"), ("a = build_list([1, 2, 3]); b = build_list([])", "to_list(merge_lists(a, b))"), ("a = build_list([]); b = build_list([0])", "to_list(merge_lists(a, b))"), ("a = build_list([1, 1]); b = build_list([1, 1])", "to_list(merge_lists(a, b))"), ("a = build_list([5, 6, 7]); b = build_list([1, 2, 3])", "to_list(merge_lists(a, b))"), ("a = build_list([-4, 0, 9]); b = build_list([-5, 1])", "to_list(merge_lists(a, b))"), ("a = build_list([2]); b = build_list([1, 3, 5, 7])", "to_list(merge_lists(a, b))")],
    "detect-cycle": [("h = build_list([])", "has_cycle(h)"), ("h = build_list([1])", "has_cycle(h)"), ("h = build_list([1]); h.next = h", "has_cycle(h)"), ("h = build_list([1, 2, 3, 4]); h.next.next.next.next = h.next", "has_cycle(h)"), ("h = build_list(list(range(20)))", "has_cycle(h)"), ("h = build_list([1, 2]); h.next.next = h", "has_cycle(h)"), ("h = build_list([5, 5, 5])", "has_cycle(h)")],
    "inorder-traversal": [("r = build_tree([])", "inorder(r)"), ("r = build_tree([1])", "inorder(r)"), ("r = build_tree([1, 2])", "inorder(r)"), ("r = build_tree([1, None, 2])", "inorder(r)"), ("r = build_tree([4, 2, 6, 1, 3, 5, 7])", "inorder(r)"), ("r = build_tree([5, 3, None, 2, None, 1])", "inorder(r)"), ("r = build_tree([1, 2, 3, 4, 5, 6, 7, 8])", "inorder(r)")],
    "search-bst": [("r = build_tree([4, 2, 7, 1, 3])", "bst_contains(r, 7)"), ("r = build_tree([4, 2, 7, 1, 3])", "bst_contains(r, 5)"), ("r = build_tree([])", "bst_contains(r, 1)"), ("r = build_tree([8])", "bst_contains(r, 8)"), ("r = build_tree([8, 3, 10, 1, 6, None, 14, None, None, 4, 7, 13])", "bst_contains(r, 13)"), ("r = build_tree([8, 3, 10, 1, 6, None, 14, None, None, 4, 7, 13])", "bst_contains(r, 9)"), ("r = build_tree([2, 1, 3])", "bst_contains(r, 1)")],
    "level-order": [("r = build_tree([])", "level_order(r)"), ("r = build_tree([1])", "level_order(r)"), ("r = build_tree([1, 2, 3, 4, 5, 6, 7])", "level_order(r)"), ("r = build_tree([1, None, 2, None, 3])", "level_order(r)"), ("r = build_tree([1, 2, None, 3, None, 4])", "level_order(r)"), ("r = build_tree([5, 4, 8, 11, None, 13, 4])", "level_order(r)"), ("r = build_tree([0, -1, 1])", "level_order(r)")],
    "apply-twice": [("", "twice(lambda x: x + 1, 5)"), ("", "twice(lambda x: x * 2, 3)"), ("", "twice(str.upper, 'hi')"), ("", "twice(lambda s: s + '!', 'hi')"), ("", "twice(lambda x: x[::-1], 'abc')"), ("", "twice(abs, 0)"), ("", "twice(lambda x: x - 10, 0)"), ("", "twice(sorted, [3, 1, 2])")],
    "transform-every-item": [("", "apply_all(str, [1, 2, 3])"), ("", "apply_all(len, ['a', 'bb', ''])"), ("", "apply_all(lambda x: x * x, [-2, 0, 3])"), ("", "apply_all(abs, [])"), ("", "apply_all(str.upper, ['x', 'y'])"), ("", "apply_all(lambda x: x + 1, [9])"), ("", "apply_all(bool, [0, '', 1, 'a'])"), ("", "apply_all(lambda w: w[0], ['cat', 'dog'])")],
    "keep-if-true": [("", "keep(lambda x: x > 2, [1, 2, 3, 4])"), ("", "keep(str.isdigit, ['1', 'a', '22'])"), ("", "keep(bool, [])"), ("", "keep(lambda x: x % 2 == 0, [1, 3, 5])"), ("", "keep(len, ['', 'a', '', 'bc'])"), ("", "keep(lambda x: True, [3, 1, 2])"), ("", "keep(lambda x: x is None, [None, 0, None])"), ("", "keep(str.isupper, ['A', 'b', 'C'])")],
    "compose-two-functions": [("", "compose(len, str)(12345)"), ("", "compose(lambda x: x + 1, lambda x: x * 2)(5)"), ("", "compose(lambda x: x * 2, lambda x: x + 1)(5)"), ("", "compose(str.upper, str.strip)('  hi ')"), ("", "compose(abs, lambda x: x - 10)(3)"), ("", "compose(sorted, list)('cab')"), ("", "compose(lambda x: x, lambda x: x)(7)"), ("", "compose(sum, lambda xs: [x * x for x in xs])([1, 2, 3])")],
    "binary-tree-maximum-depth": [("root = None", "max_depth(root)"), ("root = TreeNode(1)", "max_depth(root)"), ("root = TreeNode(1, TreeNode(2, TreeNode(3, TreeNode(4))))", "max_depth(root)"), ("root = TreeNode(1, None, TreeNode(2, None, TreeNode(3)))", "max_depth(root)"), ("root = TreeNode(1, TreeNode(2), TreeNode(3, TreeNode(4), TreeNode(5, TreeNode(6))))", "max_depth(root)"), ("root = TreeNode(0, TreeNode(0), TreeNode(0))", "max_depth(root)")],
}


# ---------------------------------------------------------------- generators for the problems added in more_*.py

def mountain(r: R) -> list[int]:
    up = sorted(r.sample(range(0, 30), r.randint(0, 5)))
    top = (up[-1] if up else 0) + r.randint(1, 5)
    down = sorted(r.sample(range(-10, top), r.randint(0, 5)), reverse=True)
    return up + [top] + down


def undo_actions(r: R) -> list[list[str]]:
    return [["undo"] if r.random() < 0.3 else ["type", r.choice("abcxyz!")] for _ in range(r.randint(0, 9))]


def tag_list(r: R) -> list[str]:
    names = "abip"
    if r.random() < 0.5:  # a well-formed list, built from nested pairs
        out: list[str] = []
        stack: list[str] = []
        for _ in range(r.randint(0, 8)):
            if stack and r.random() < 0.5:
                out.append(f"</{stack.pop()}>")
            else:
                name = r.choice(names)
                stack.append(name)
                out.append(f"<{name}>")
        while stack:
            out.append(f"</{stack.pop()}>")
        return out
    return [r.choice([f"<{n}>", f"</{n}>"]) for n in r.choices(names, k=r.randint(1, 6))]


def max_stack_ops(r: R) -> list[list[Any]]:
    ops: list[list[Any]] = []
    size = 0
    for _ in range(r.randint(1, 10)):
        kind = r.choice(["push", "push", "pop", "max"]) if size else "push"
        if kind == "push":
            ops.append(["push", r.randint(-9, 9)])
            size += 1
        else:
            ops.append([kind])
            size -= kind == "pop"
    return ops


def directed_edges(r: R, n: int) -> list[list[int]]:
    pairs = [[a, b] for a in range(n) for b in range(n) if a != b]
    return r.sample(pairs, r.randint(0, min(len(pairs), n + 2)))


def symmetric_table(r: R) -> list[list[int]]:
    n = r.randint(1, 6)
    table = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if r.random() < 0.3:
                table[i][j] = table[j][i] = 1
    return table


def triangle(r: R) -> list[list[int]]:
    return [[r.randint(-5, 9) for _ in range(i + 1)] for i in range(r.randint(1, 6))]


def iso_date(r: R) -> str:
    return f"{r.randint(1990, 2030)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}"


def k_window(r: R) -> list[Any]:
    nums = ints(r, r.randint(1, 9), -5, 9)
    return [nums, r.randint(1, len(nums))]


def number_text(r: R) -> str:
    return r.choice([str(r.randint(-999, 999)), f"{r.uniform(-50, 50):.2f}", word(r, 1, 5, "abcxyz"), f"{r.randint(1, 9)}{r.choice('ab.')}{r.randint(0, 9)}", ""])


def any_value(r: R) -> Any:
    return r.choice([r.randint(-50, 50), round(r.uniform(-5, 5), 1), word(r, 0, 4, "abc"), ints(r, r.randint(0, 3), 0, 9)])


def bst_values(r: R, lo: int = 2) -> tuple[list[Any], list[int]]:
    return bst(r, r.randint(lo, 9), 1, 40)


GENERATORS.update({
    # basics, input and output, decisions, loops, functions, strings, lists and dictionaries
    "shout-it-back": lambda r: sentence(r, 1, 4, "abcXYZ") + "\n",
    "say-it-three-times": lambda r: word(r, 1, 8, "abcdeXYZ19") + "\n",
    "classify-number-text": lambda r: [number_text(r)],
    "join-as-text": lambda r: [any_value(r), any_value(r)],
    "double-anything": lambda r: [any_value(r)],
    "age-next-year": lambda r: f"{r.choice(['Ada', 'Bo', 'Priya', 'Kenji', 'Sofia', 'Omar', 'Lena', 'Ravi'])}\n{r.randint(0, 110)}\n",
    "total-of-one-line": lambda r: " ".join(str(r.randint(-50, 99)) for _ in range(r.randint(0, 7))) + "\n",
    "percentage-score": lambda r: (lambda total: f"{r.randint(0, total)}\n{total}\n")(r.randint(1, 200)),
    "price-with-tax": lambda r: f"{r.randint(0, 5000) / 100}\n{r.choice([0, 5, 7.5, 10, 12, 18, 20, 25])}\n",
    "position-of-the-largest": lambda r: [ints(r, r.randint(1, 9), -9, 9)],
    "best-scoring-word": lambda r: [[word(r, 1, 5, "abcxyz") for _ in range(r.randint(0, 6))]],
    "matrix-column-sums": lambda r: [grid(r, r.randint(1, 4), r.randint(1, 4), tuple(range(-5, 10)))],
    "identity-matrix": lambda r: [r.randint(0, 7)],
    # algorithms
    "top-of-the-mountain": lambda r: [mountain(r)],
    "fairest-split": lambda r: (lambda nums: [nums, r.randint(1, len(nums))])(ints(r, r.randint(1, 9), 0, 20)),
    "sort-by-frequency": lambda r: [ints(r, r.randint(0, 10), 0, 5)],
    "closest-value-in-sorted-list": lambda r: [sorted(ints(r, r.randint(1, 8), -20, 20)), r.randint(-25, 25)],
    "pair-sum-closest-to-target": lambda r: [sorted(ints(r, r.randint(2, 8), -20, 20)), r.randint(-30, 30)],
    "windows-reaching-a-total": lambda r: (lambda nums: [nums, r.randint(1, len(nums)), r.randint(-5, 20)])(ints(r, r.randint(1, 9), -5, 9)),
    "smallest-spread-of-k-values": k_window,
    "most-common-words": lambda r: [" ".join(r.choice(["go", "Go", "stop", "the", "a", "cat", "Cat", "run"]) for _ in range(r.randint(0, 9))), r.randint(0, 4)],
    # structures
    "typing-with-undo": lambda r: [undo_actions(r)],
    "tags-close-in-order": lambda r: [tag_list(r)],
    "max-stack": lambda r: [max_stack_ops(r)],
    "sliding-window-minimum": k_window,
    "largest-value-in-a-linked-list": lambda r: [ints(r, r.randint(1, 9))],
    "count-a-value-in-a-linked-list": lambda r: [ints(r, r.randint(0, 8), 0, 4), r.randint(0, 5)],
    "insert-at-a-position": lambda r: (lambda nums: [nums, r.randint(0, len(nums)), r.randint(0, 9)])(ints(r, r.randint(0, 7), 0, 9)),
    "delete-the-middle-node": lambda r: [ints(r, r.randint(0, 9), 0, 9)],
    "weave-two-lists": lambda r: [ints(r, r.randint(0, 5), 0, 9), ints(r, r.randint(0, 5), 0, 9)],
    "remove-repeats-from-unsorted-list": lambda r: [ints(r, r.randint(0, 9), 0, 5)],
    "split-a-list-in-half": lambda r: [ints(r, r.randint(0, 9), 0, 9)],
    "largest-value-in-a-tree": lambda r: [random_tree(r, r.randint(1, 9))],
    "total-of-each-level": lambda r: [random_tree(r, r.randint(0, 10))],
    "shallowest-leaf": lambda r: [random_tree(r, r.randint(0, 10))],
    "total-within-a-range": lambda r: (lambda t, low: [t[0], low, low + r.randint(0, 20)])(bst_values(r, 1), r.randint(0, 30)),
    "best-root-to-leaf-total": lambda r: [random_tree(r, r.randint(1, 9), -9, 9)],
    "nodes-with-no-larger-ancestor": lambda r: [random_tree(r, r.randint(0, 10), 0, 9)],
    "smallest-gap-in-a-search-tree": lambda r: [bst_values(r)[0]],
    "widest-level": lambda r: [random_tree(r, r.randint(0, 12))],
    "directed-adjacency-lists": lambda r: (lambda n: [n, directed_edges(r, n)])(r.randint(1, 5)),
    "how-many-can-be-reached": lambda r: (lambda g: [g, r.randrange(len(g))])(adjacency(r, r.randint(1, 6))),
    "island-coastline": lambda r: [grid(r, r.randint(1, 5), r.randint(1, 5))],
    "fewest-knight-moves": lambda r: (lambda n: [n, [r.randrange(n), r.randrange(n)], [r.randrange(n), r.randrange(n)]])(r.randint(1, 8)),
    "fewest-terms-to-finish": lambda r: (lambda n: [n, dag_rules(r, n, r.randint(0, n + 2))])(r.randint(1, 6)),
    "is-it-a-tree": lambda r: (lambda n: [n, undirected_edges(r, n, max(0, n - 1 + r.choice([-1, 0, 0, 1])))])(r.randint(1, 6)),
    "groups-from-a-friendship-table": lambda r: [symmetric_table(r)],
    # dynamic programming and the toolkit
    "cheapest-path-down-a-triangle": lambda r: [triangle(r)],
    "days-between-dates": lambda r: [iso_date(r), iso_date(r)],
})

GENERATORS.update({
    # small inputs, where the examples alone give too few different values
    "star-triangle-rows": lambda r: [r.randint(0, 15)],
    "recursive-factorial": lambda r: [r.randint(0, 20)],
    "count-down-list": lambda r: [r.randint(0, 25)],
    "reverse-in-place": lambda r: [ints(r, r.randint(0, 9), -9, 9)],
    "all-bit-strings": lambda r: [r.randint(0, 8)],
    "identity-matrix": lambda r: [r.randint(0, 10)],
    "order-people-by-age": lambda r: [[[name, r.randint(1, 9)] for name in r.sample(["al", "bo", "cy", "di", "ed", "flo", "gus"], r.randint(0, 6))]],
    "keys-with-a-value": lambda r: [{k: r.randint(0, 3) for k in r.sample("abcdefg", r.randint(0, 6))}, r.randint(0, 3)],
    "pass-and-leave": lambda r: [r.sample(["a", "b", "c", "d", "e", "f", "g", "h"], r.randint(0, 8)), r.randint(1, 6)],
    "closest-split-into-two-groups": lambda r: [ints(r, r.randint(0, 8), 0, 30)],
    "first-character-to-repeat": lambda r: [word(r, 0, 9, "abcdefg")],
    "grid-paths-with-diagonal-steps": lambda r: [r.randint(1, 8), r.randint(1, 8)],
    "join-words": lambda r: [[word(r, 1, 4, "abcxyz") for _ in range(r.randint(0, 5))]] + ([r.choice(["", "-", ", ", " | ", "_"])] if r.random() < 0.6 else []),
    "repeat-text": lambda r: [word(r, 0, 4, "abc-")] + ([r.randint(0, 5)] if r.random() < 0.6 else []),
    "many-trades": lambda r: [ints(r, r.randint(0, 9), 1, 20)],
    "same-sign": lambda r: [r.choice([0, r.randint(-9, 9)]), r.choice([0, r.randint(-9, 9)])],
    "safe-item-lookup": lambda r: (lambda items: [items, r.randint(-len(items) - 2, len(items) + 2)] + ([r.choice([0, -1, "none", None])] if r.random() < 0.5 else []))(ints(r, r.randint(0, 5), 0, 9)),
})

GENERATORS.update({
    # text problems where random letters almost never give an interesting answer
    "rotation-of-another-string": lambda r: (lambda a: [a, (lambda k: a[k:] + a[:k])(r.randint(0, len(a))) if r.random() < 0.6 else word(r, len(a), len(a), "abc") if a else ""])(word(r, 0, 7, "abc")),
    "longest-shared-stretch-of-text": lambda r: [word(r, 0, 9, "ab"), word(r, 0, 9, "ab")],
    "where-rearrangements-start": lambda r: [word(r, 0, 10, "ab"), word(r, 0, 3, "ab")],
})


# ---------------------------------------------------------------- large inputs
# Answers stay short (a number, a pair, True or False), because the sandbox caps output at 64 KB.
# About 2,000 values checks the code finishes in time. EFFICIENCY problems ask for a fast approach in their task,
# so they also get 20,000 values, where a quadratic solution runs out of time and the intended one does not.

N = 2000
BIG = 20000


def _distinct_evens(r: R, n: int) -> list[int]:
    return [2 * v for v in r.sample(range(-500000, 500000), n)]


def _two_sum_large(r: R, n: int) -> list[Any]:
    """Distinct even numbers plus exactly two odd ones near the end: only that pair can add up to the odd target."""
    nums = _distinct_evens(r, n - 2)
    a, b = 2 * r.randint(-400000, 400000) + 1, 2 * r.randint(-400000, 400000) + 1
    while b == a:
        b += 2
    nums.insert(len(nums) - r.randint(0, 50), a)
    nums.insert(len(nums) - r.randint(0, 50), b)
    return [nums, a + b]


def _first_duplicate_large(r: R, n: int) -> list[Any]:
    nums = r.sample(range(1, 10 * n), n - 1)
    return [nums + [nums[r.randrange(n // 2)]]]


def _rotated_large(r: R, n: int) -> list[int]:
    nums = sorted(r.sample(range(-10 * n, 10 * n), n))
    k = r.randrange(n)
    return nums[k:] + nums[:k]


def _reachable_large(r: R, n: int) -> list[int]:
    return [r.randint(1, 4) for _ in range(n)]


LARGE: dict[str, Callable[[R], Any]] = {
    "binary-search": lambda r: (lambda nums: [nums, r.choice(nums)])(sorted(r.sample(range(-50000, 50000), N))),
    "linear-search-index": lambda r: [ints(r, N, 0, 500), r.randint(0, 600)],
    "first-position-sorted": lambda r: [sorted(ints(r, N, 0, 300)), r.randint(0, 300)],
    "last-position-sorted": lambda r: [sorted(ints(r, N, 0, 300)), r.randint(0, 300)],
    "insert-position-sorted": lambda r: [sorted(ints(r, N, 0, 5000)), r.randint(-10, 5010)],
    "count-in-sorted": lambda r: [sorted(ints(r, N, 0, 200)), r.randint(0, 200)],
    "search-rotated-list": lambda r: (lambda nums: [nums, r.choice(nums)])(_rotated_large(r, N)),
    "rotation-minimum": lambda r: [_rotated_large(r, N)],
    "smallest-eating-speed": lambda r: (lambda piles: [piles, r.randint(len(piles), 3 * len(piles))])(ints(r, N, 1, 100000)),
    "split-into-days": lambda r: [ints(r, N, 1, 500), r.randint(1, 60)],
    "kth-largest-value": lambda r: [ints(r, N, -1000, 1000), r.randint(1, N)],
    "pair-sum-exists-sorted": lambda r: [sorted(ints(r, N, -10000, 10000)), r.randint(-20000, 20000)],
    "container-with-most-water": lambda r: [ints(r, N, 0, 10000)],
    "trapped-rain-water": lambda r: [ints(r, N, 0, 1000)],
    "unique-count-sorted": lambda r: [sorted(ints(r, N, 0, 700))],
    "longest-all-same-run": lambda r: [ints(r, N, 0, 2)],
    "max-average-window": lambda r: [ints(r, N, -100, 100), r.randint(1, 300)],
    "max-window-sum": lambda r: [ints(r, N, -100, 100), r.randint(1, 300)],
    "shortest-window-with-sum": lambda r: [ints(r, N, 1, 50), r.randint(1, 20000)],
    "longest-no-repeat-substring": lambda r: [word(r, 3000, 3000, "abcdefghijklmnop")],
    "longest-with-k-distinct": lambda r: [word(r, 3000, 3000, "abcdefg"), r.randint(1, 6)],
    "flip-zeros-longest-ones": lambda r: [ints(r, N, 0, 1), r.randint(0, 60)],
    "balance-point-index": lambda r: [ints(r, N, -50, 50)],
    "largest-stretch-sum": lambda r: [ints(r, N, -100, 100)],
    "best-buy-then-sell": lambda r: [ints(r, N, 1, 1000)],
    "first-missing-positive": lambda r: [ints(r, N, -10, 2500)],
    "has-duplicate-value": lambda r: [r.sample(range(10 * N), N)],
    "first-repeated-value": lambda r: _first_duplicate_large(r, N),
    "first-unique-character": lambda r: [word(r, 5000, 5000, "abcdefghij") + "z"],
    "longest-without-repeat-values": lambda r: [ints(r, N, 0, 40)],
    "missing-number-in-range": lambda r: (lambda nums: [r.sample(nums, len(nums))])((lambda gap: [v for v in range(N + 1) if v != gap])(r.randint(0, N))),
    "house-robber": lambda r: [ints(r, N, 0, 100)],
    "min-cost-stairs": lambda r: [ints(r, N, 0, 100)],
    "min-jumps-to-end": lambda r: [_reachable_large(r, N)],
    "longest-common-subsequence": lambda r: [word(r, 400, 400, "abcd"), word(r, 400, 400, "abcd")],
    "edit-distance-words": lambda r: [word(r, 250, 250, "abcde"), word(r, 250, 250, "abcde")],
    "fewest-coins": lambda r: [[1, 5, 7, 11, 23], r.randint(2000, 5000)],
    "fairest-split": lambda r: (lambda nums: [nums, r.randint(1, 60)])(ints(r, N, 0, 100)),
    "windows-reaching-a-total": lambda r: [ints(r, N, -5, 9), r.randint(1, 200), r.randint(0, 600)],
    "pair-sum-closest-to-target": lambda r: [sorted(ints(r, N, -10000, 10000)), r.randint(-20000, 20000)],
    "smallest-spread-of-k-values": lambda r: [ints(r, N, -100000, 100000), r.randint(1, N)],
    "position-of-the-largest": lambda r: [ints(r, N, -100000, 100000)],
    "below-the-average": lambda r: [ints(r, N, -1000, 1000)],
    # the task asks for an efficient approach, so these also get very large inputs
    "two-sum-fast": lambda r: _two_sum_large(r, N),
    "identify-duplicate-o-n": lambda r: _first_duplicate_large(r, N),
    "count-pairs-with-sum-fast": lambda r: [ints(r, N, 0, 50), 50],
    "longest-consecutive-run": lambda r: [r.sample(range(3 * N), N)],
    "count-subarrays-with-sum": lambda r: [ints(r, N, -3, 3), 2],
    "longest-zero-sum-stretch": lambda r: [ints(r, N, -3, 3)],
}
EFFICIENCY: dict[str, Callable[[R], Any]] = {
    "two-sum-fast": lambda r: _two_sum_large(r, BIG),
    "identify-duplicate-o-n": lambda r: _first_duplicate_large(r, BIG),
    "count-pairs-with-sum-fast": lambda r: [ints(r, BIG, 0, 50), 50],
    "longest-consecutive-run": lambda r: [r.sample(range(3 * BIG), BIG)],
    "count-subarrays-with-sum": lambda r: [ints(r, BIG, -3, 3), 2],
    "longest-zero-sum-stretch": lambda r: [ints(r, BIG, -3, 3)],
}


# ---------------------------------------------------------------- statement scripts: (setup, expression)
# For classes, generators and functions that take functions. Each script is a valid sequence of calls.

def _ctor(tree: list[Any]) -> str:
    """Nested TreeNode(...) code for a level-order list, for tasks that build trees by hand."""
    if not tree or tree[0] is None:
        return "None"
    nodes = [None if v is None else [v, None, None] for v in tree]
    children = iter(nodes[1:])
    for node in nodes:
        if node is None:
            continue
        node[1], node[2] = next(children, None), next(children, None)

    def code(node: list[Any] | None) -> str:
        if node is None:
            return "None"
        if node[1] is None and node[2] is None:
            return f"TreeNode({node[0]})"
        return f"TreeNode({node[0]}, {code(node[1])}, {code(node[2])})"
    return code(nodes[0])


SHAPE = "(lambda f, n: f(f, n))(lambda f, n: None if n is None else [n.val, f(f, n.left), f(f, n.right)], {0})"
NUMBER_FUNCTIONS = ["lambda x: x + 1", "lambda x: x * 2", "lambda x: x - 3", "lambda x: x * x", "abs", "lambda x: -x", "lambda x: x // 2", "lambda x: x % 5"]
TEXT_FUNCTIONS = ["str.upper", "str.lower", "lambda s: s[::-1]", "lambda s: s + '!'", "lambda s: s[1:]", "str.strip"]
NUMBER_TESTS = ["lambda x: x > 2", "lambda x: x % 2 == 0", "lambda x: x < 0", "lambda x: x == 0", "bool", "lambda x: x in (1, 3, 5)"]


def _ops_bank(r: R) -> tuple[str, str]:
    lines = [f"a = BankAccount('Bo', {r.choice([0, 10, 50, 100])})"]
    for _ in range(r.randint(0, 6)):
        lines.append(f"a.{r.choice(['deposit', 'withdraw'])}({r.choice([0, -5, 5, 20, 60, 200])})")
    return "\n".join(lines), r.choice(["a.get_balance()", f"a.withdraw({r.choice([1, 30, 500])})", f"a.deposit({r.choice([-1, 15])})"])


def _ops_stack_queue(r: R) -> tuple[str, str]:
    lines, size = ["q = StackQueue()"], 0
    for _ in range(r.randint(0, 8)):
        if size and r.random() < 0.4:
            lines.append("q.pop()")
            size -= 1
        else:
            lines.append(f"q.push({r.randint(-9, 9)})")
            size += 1
    return "\n".join(lines), r.choice(["q.size()", f"[q.pop() for _ in range({size})]"] if size else ["q.size()"])


def _ops_stack(r: R) -> tuple[str, str]:
    lines, size = ["s = Stack()"], 0
    for _ in range(r.randint(0, 8)):
        if r.random() < 0.35:
            lines.append("s.pop()")
            size = max(0, size - 1)
        else:
            lines.append(f"s.push({r.choice([r.randint(-9, 9), repr(word(r, 1, 3))])})")
            size += 1
    return "\n".join(lines), r.choice(["s.size()", "s.peek()", "s.pop()", f"[s.pop() for _ in range({size + 1})]"])


def _ops_cart(r: R) -> tuple[str, str]:
    lines = ["c = Cart()"]
    for _ in range(r.randint(0, 6)):
        item = r.choice(["tea", "jam", "bun"])
        if r.random() < 0.3:
            lines.append(f"c.remove({item!r})")
        elif r.random() < 0.5:
            lines.append(f"c.add({item!r}, {r.randint(0, 9)})")
        else:
            lines.append(f"c.add({item!r}, {r.randint(0, 9)}, {r.randint(0, 4)})")
    return "\n".join(lines), "c.total()"


def _ops_counter(r: R) -> tuple[str, str]:
    lines = ["c = Counter()"]
    for _ in range(r.randint(0, 6)):
        lines.append(r.choice(["c.increment()", f"c.increment({r.randint(-3, 9)})", f"c.increment(step={r.randint(0, 5)})"]))
    return "\n".join(lines), "c.get_count()"


def _ops_point(r: R) -> tuple[str, str]:
    lines = [f"p = Point({r.randint(-9, 9)}, {r.randint(-9, 9)})"]
    for _ in range(r.randint(0, 4)):
        lines.append(f"p.move({r.randint(-5, 5)}, {r.randint(-5, 5)})")
    return "\n".join(lines), r.choice(["(p.x, p.y)", "p.x", "p.y"])


def _detect_cycle(r: R) -> tuple[str, str]:
    values = ints(r, r.randint(0, 9), 0, 9)
    if values and r.random() < 0.5:
        target = r.randrange(len(values))
        setup = (f"h = build_list({values!r})\ntail = h\nwhile tail.next:\n    tail = tail.next\nnode = h\n"
                 f"for _ in range({target}):\n    node = node.next\ntail.next = node")
    else:
        setup = f"h = build_list({values!r})"
    return setup, "has_cycle(h)"


SCRIPTS: dict[str, Callable[[R], tuple[str, str]]] = {
    "bank-account-class": _ops_bank,
    "queue-from-two-stacks": _ops_stack_queue,
    "build-a-stack-class": _ops_stack,
    "shopping-cart-class": _ops_cart,
    "counter-class": _ops_counter,
    "point-class": _ops_point,
    "rectangle-area": lambda r: (f"r = Rectangle({r.choice([r.randint(0, 40), round(r.uniform(0, 20), 1)])}, {r.randint(0, 40)})", "r.area()"),
    "square-inherits-rectangle": lambda r: (f"s = Square({r.choice([r.randint(0, 50), round(r.uniform(0, 9), 1)])})", r.choice(["s.area()", "isinstance(s, Rectangle)", "s.width + s.height"])),
    "temperature-converter-class": lambda r: (f"t = Temperature({r.choice([r.randint(-60, 120), round(r.uniform(-50, 50), 1)])})", r.choice(["t.to_fahrenheit()", "t.to_kelvin()", "t.celsius"])),
    "custom-range-iterator": lambda r: ("", f"list(RangeIterator({r.randint(-10, 15)}, {r.randint(-10, 25)}))"),
    "even-number-generator": lambda r: ("", r.choice([f"list(even_generator({r.randint(-3, 60)}))", f"sum(even_generator({r.randint(0, 200)}))"])),
    "countdown-generator": lambda r: ("", r.choice([f"list(countdown({r.randint(-5, 40)}))", f"sum(countdown({r.randint(0, 300)}))"])),
    "chunks-generator": lambda r: ("", f"list(chunks({ints(r, r.randint(0, 12), 0, 9)!r}, {r.randint(1, 6)}))"),
    "multiplier-factory": lambda r: (f"f = make_multiplier({r.randint(-5, 9)})", f"f({r.choice([r.randint(-20, 20), round(r.uniform(-5, 5), 1)])})"),
    "apply-twice": lambda r: ("", r.choice([f"twice({r.choice(NUMBER_FUNCTIONS)}, {r.randint(-20, 20)})", f"twice({r.choice(TEXT_FUNCTIONS)}, {word(r, 0, 6, 'abcXY ')!r})"])),
    "transform-every-item": lambda r: ("", r.choice([f"apply_all({r.choice(NUMBER_FUNCTIONS)}, {ints(r, r.randint(0, 6))!r})", f"apply_all({r.choice(TEXT_FUNCTIONS + ['len'])}, {[word(r, 0, 4, 'abcX') for _ in range(r.randint(0, 5))]!r})"])),
    "keep-if-true": lambda r: ("", f"keep({r.choice(NUMBER_TESTS)}, {ints(r, r.randint(0, 8))!r})"),
    "count-matching-items": lambda r: ("", f"count_if({r.choice(NUMBER_TESTS)}, {ints(r, r.randint(0, 9))!r})"),
    "compose-two-functions": lambda r: ("", f"compose({r.choice(NUMBER_FUNCTIONS)}, {r.choice(NUMBER_FUNCTIONS)})({r.randint(-20, 20)})"),
    "apply-n-times": lambda r: ("", f"apply_n({r.choice(NUMBER_FUNCTIONS)}, {r.randint(-10, 10)}, {r.randint(0, 6)})"),
    "sort-tuples-by-second-item": lambda r: ("", f"sort_by_second({[(word(r, 1, 2, 'abc'), r.randint(-5, 9)) for _ in range(r.randint(0, 7))]!r})"),
    "invert-dictionary": lambda r: ("", f"invert_dict({dict(zip(r.sample('abcdefgh', k := r.randint(0, 6)), r.sample(range(-9, 30), k)))!r})"),
    "reverse-linked-list": lambda r: (f"h = build_list({ints(r, r.randint(0, 10))!r})", "to_list(reverse_list(h))"),
    "middle-of-linked-list": lambda r: (f"h = build_list({ints(r, r.randint(1, 11))!r})", r.choice(["middle_node(h).val", "to_list(middle_node(h))"])),
    "merge-two-linked-lists": lambda r: (f"a = build_list({sorted(ints(r, r.randint(0, 6)))!r}); b = build_list({sorted(ints(r, r.randint(0, 6)))!r})", "to_list(merge_lists(a, b))"),
    "detect-cycle": _detect_cycle,
    "inorder-traversal": lambda r: (f"r = build_tree({random_tree(r, r.randint(0, 10))!r})", "inorder(r)"),
    "level-order": lambda r: (f"r = build_tree({random_tree(r, r.randint(0, 10))!r})", "level_order(r)"),
    "search-bst": lambda r: (lambda t: (f"r = build_tree({t[0]!r})", f"bst_contains(r, {r.choice(t[1]) if r.random() < 0.5 else r.randint(0, 45)})"))(bst(r, r.randint(1, 9))),
    "binary-tree-maximum-depth": lambda r: (f"root = {_ctor(random_tree(r, r.randint(0, 10)))}", "max_depth(root)"),
    "invert-binary-tree": lambda r: (f"root = {_ctor(random_tree(r, r.randint(1, 10)))}\ninv = invert_tree(root)", SHAPE.format("inv")),
}

GENERATORS.update({
    # wider ranges than the examples happened to show, all within what the task allows
    "fizz-word": lambda r: [r.randint(1, 3000)],
    "even-or-odd-checker": lambda r: [r.randint(-10000, 10000)],
    "is-happy-number": lambda r: [r.randint(1, 5000)],
    "collatz-steps": lambda r: [r.randint(1, 10000)],
    "factorial-with-a-loop": lambda r: [r.randint(0, 60)],
    "recursive-factorial": lambda r: [r.randint(0, 60)],
    "tower-of-hanoi-moves": lambda r: [r.randint(0, 60)],
    "climbing-stairs": lambda r: [r.randint(0, 80)],
    "tribonacci-values": lambda r: [r.randint(0, 70)],
    "count-down-list": lambda r: [r.randint(0, 120)],
    "star-triangle-rows": lambda r: [r.randint(0, 30)],
    "row-of-pascals-triangle": lambda r: [r.randint(0, 30)],
    "fibonacci-recursive": lambda r: [r.randint(0, 22)],
    "circle-area": lambda r: [r.choice([r.randint(0, 100), round(r.uniform(0, 50), 1)])],
    "describe-type-name": lambda r: [r.choice([r.randint(-99, 99), round(r.uniform(-9, 9), 2), word(r, 0, 5), True, False, None, ints(r, r.randint(0, 3)),
                                              {word(r, 1, 3): r.randint(0, 9)}, 0.0, "", []])],
    "greet-by-name": lambda r: (word(r, 1, 1, "BCDFGHJKLMNPRSTVWZ") + word(r, 1, 6, "aeiourlnst")) + "\n",
    "recent-counter-queue-processor": lambda r: [[r.choice(["job", "task", "req"]) + str(r.randint(1, 99)) for _ in range(r.randint(0, 9))]],
    "read-a-number-safely": lambda r: [number_text(r)] + ([r.choice([0, -1, 99, None])] if r.random() < 0.5 else []),
    "almost-a-palindrome": lambda r: (lambda half: [half + half[::-1][r.randint(0, 1):] if r.random() < 0.5 else (lambda w: w[:k] + r.choice("abc") + w[k:])(half + half[::-1]) if (k := r.randint(0, len(half))) or True else ""])(word(r, 0, 5, "abc")),
})


def _near_palindrome(r: R) -> list[str]:
    """A palindrome, one with a single extra letter somewhere, or one with two changes."""
    half = word(r, 0, 5, "abc")
    text = half + half[::-1][r.randint(0, 1):] if half else ""
    kind = r.random()
    if kind < 0.35 or not text:
        return [text]
    position = r.randint(0, len(text))
    text = text[:position] + r.choice("abcd") + text[position:]
    if kind > 0.75:
        position = r.randrange(len(text))
        text = text[:position] + r.choice("xyz") + text[position + 1:]
    return [text]


GENERATORS["almost-a-palindrome"] = _near_palindrome

GENERATORS.update({
    "identity-matrix": lambda r: [r.randint(0, 40)],
    "multiplication-grid": lambda r: [r.randint(0, 40)],
})


# ---------------------------------------------------------------- yes-or-no tasks: include the rare answer on purpose
# Random inputs almost never form a right triangle or a perfect number, so the tests would be nearly all one answer.

def _right_triangle(r: R) -> list[int]:
    if r.random() < 0.45:
        a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29)])
        k = r.randint(1, 6)
        sides = [a * k, b * k, c * k]
        r.shuffle(sides)
        return sides
    return [r.randint(1, 30) for _ in range(3)]


def _interleave(r: R) -> list[str]:
    a, b = word(r, 0, 4, "ab"), word(r, 0, 4, "cd")
    if r.random() < 0.5:
        i = j = 0
        out = []
        while i < len(a) or j < len(b):
            if j >= len(b) or (i < len(a) and r.random() < 0.5):
                out.append(a[i])
                i += 1
            else:
                out.append(b[j])
                j += 1
        return [a, b, "".join(out)]
    mixed = list(a + b)
    r.shuffle(mixed)
    return [a, b, "".join(mixed)]


def _balanced_brackets(r: R) -> list[str]:
    if r.random() < 0.5:
        out, stack = [], []
        for _ in range(r.randint(0, 6)):
            if stack and r.random() < 0.45:
                out.append({"(": ")", "[": "]", "{": "}"}[stack.pop()])
            else:
                opener = r.choice("([{")
                stack.append(opener)
                out.append(opener)
        while stack:
            out.append({"(": ")", "[": "]", "{": "}"}[stack.pop()])
        return ["".join(out)]
    return ["".join(r.choice("()[]{}") for _ in range(r.randint(1, 10)))]


GENERATORS.update({
    "right-triangle-identifier": _right_triangle,
    "perfect-number-check": lambda r: [r.choice([6, 28, 496, 8128]) if r.random() < 0.35 else r.randint(1, 10000)],
    "armstrong-number": lambda r: [r.choice([0, 1, 5, 9, 153, 370, 371, 407, 1634, 8208, 9474, 54748]) if r.random() < 0.4 else r.randint(0, 99999)],
    "valid-anagram-counts": lambda r: (lambda a: [a, "".join(r.sample(a, len(a))) if r.random() < 0.5 else word(r, len(a), len(a), "abc")])(word(r, 0, 7, "abc")),
    "interleaving-strings-check": _interleave,
    "sign-of-number": lambda r: [r.choice([0, r.randint(-500, -1), r.randint(1, 500)])],
    "valid-parentheses": _balanced_brackets,
})
