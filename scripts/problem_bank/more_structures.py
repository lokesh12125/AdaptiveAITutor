"""More problems for stacks and queues, linked lists, trees and graphs."""
from dsl import fn, linked, tree

U = "stacks-queues"
fn("typing-with-undo", "Typing With Undo", U, "easy", "Stack basics",
   'Write `final_text(actions)`. Each action is `["type", ch]`, which adds one character, or `["undo"]`, which removes the most recently added character still there. Undo with nothing typed does nothing. Return the final text.',
   '''def final_text(actions):
    typed = []
    for action in actions:
        if action[0] == "type":
            typed.append(action[1])
        elif typed:
            typed.pop()
    return "".join(typed)''', [([["type", "a"], ["type", "b"], ["undo"], ["type", "c"]], "ac"), ([["undo"]], "")],
   [[], [["type", "x"]], [["type", "a"], ["undo"], ["undo"]], [["type", "h"], ["type", "i"], ["type", "!"]], [["undo"], ["type", "z"], ["undo"], ["type", "y"]]])
fn("tags-close-in-order", "Tags Close in Order", U, "medium", "Matching and parsing",
   'Write `tags_ok(tags)` for a list of tags such as `"<b>"` and `"</b>"`. Return True when every opening tag is closed by its own closing tag, in the right order, and nothing is left open.',
   '''def tags_ok(tags):
    stack = []
    for tag in tags:
        if tag.startswith("</"):
            if not stack or stack.pop() != tag[2:-1]:
                return False
        else:
            stack.append(tag[1:-1])
    return not stack''', [(["<a>", "<b>", "</b>", "</a>"], True), (["<a>", "<b>", "</a>", "</b>"], False)],
   [[], ["<p>"], ["</p>"], ["<i>", "</i>", "<b>", "</b>"], ["<x>", "<x>", "</x>", "</x>"], ["<a>", "</b>"]])
fn("previous-smaller-value", "Previous Smaller Value", U, "medium", "Monotonic stack",
   "Write `previous_smaller(nums)` for a list of non-negative numbers, returning for each position the nearest earlier value that is strictly smaller, or -1 when there is none. Keep a stack of values that could still be the answer for later positions.",
   '''def previous_smaller(nums):
    out, stack = [], []
    for n in nums:
        while stack and stack[-1] >= n:
            stack.pop()
        out.append(stack[-1] if stack else -1)
        stack.append(n)
    return out''', [([4, 5, 2, 10, 8], [-1, 4, -1, 2, 2]), ([], [])], [[1], [1, 2, 3], [3, 2, 1], [2, 2, 2], [0, 7, 3, 9, 1, 5]])
fn("price-span", "Price Span", U, "medium", "Monotonic stack",
   "Write `spans(prices)` returning, for each day, how many days in a row ending today had a price no higher than today's, counting today. A stack of earlier prices with their spans lets you jump back over days already counted.",
   '''def spans(prices):
    out, stack = [], []
    for price in prices:
        span = 1
        while stack and stack[-1][0] <= price:
            span += stack.pop()[1]
        stack.append((price, span))
        out.append(span)
    return out''', [([100, 80, 60, 70, 60, 75, 85], [1, 1, 1, 2, 1, 4, 6]), ([], [])], [[5], [1, 2, 3], [3, 2, 1], [2, 2, 2], [10, 4, 5, 90, 120, 80]])
fn("pass-and-leave", "Pass and Leave", U, "medium", "Queue and deque",
   "People stand in a circle in the given order. Starting from the first, count k people, and the k-th person leaves. Counting starts again from the next person. Write `leave_order(names, k)` returning the names in the order they leave. A deque that you rotate is a natural fit.",
   '''from collections import deque

def leave_order(names, k):
    circle = deque(names)
    out = []
    while circle:
        circle.rotate(-(k - 1))
        out.append(circle.popleft())
    return out''', [((["a", "b", "c", "d"], 2), ["b", "d", "c", "a"]), ((["x"], 3), ["x"])], [([], 1), (["a", "b", "c"], 1), (["a", "b", "c"], 3), (["p", "q", "r", "s", "t"], 7)])
fn("max-stack", "Max Stack", U, "medium", "Design with stacks and queues",
   'Write `max_stack(ops)`. Each operation is `["push", x]`, `["pop"]` or `["max"]`. Return a list of what each pop removes and what each max reports, in order. Operations are always valid, so the stack is never empty for pop or max. Keep a second stack holding the largest value at each height.',
   '''def max_stack(ops):
    stack, maxes, out = [], [], []
    for op in ops:
        if op[0] == "push":
            stack.append(op[1])
            maxes.append(op[1] if not maxes else max(op[1], maxes[-1]))
        elif op[0] == "pop":
            maxes.pop()
            out.append(stack.pop())
        else:
            out.append(maxes[-1])
    return out''', [([["push", 1], ["push", 5], ["max"], ["pop"], ["max"]], [5, 5, 1]), ([], [])],
   [[["push", 3]], [["push", 2], ["push", 2], ["pop"], ["max"]], [["push", -1], ["max"], ["push", -5], ["max"], ["pop"], ["pop"]]])
fn("sliding-window-minimum", "Sliding Window Minimum", U, "hard", "Queue and deque",
   "Write `window_mins(nums, k)` returning the smallest value in each window of k neighbouring numbers, from left to right. k is between 1 and the length of the list. Keep a deque of positions whose values increase from front to back.",
   '''from collections import deque

def window_mins(nums, k):
    out, window = [], deque()
    for i, n in enumerate(nums):
        while window and nums[window[-1]] >= n:
            window.pop()
        window.append(i)
        if window[0] <= i - k:
            window.popleft()
        if i >= k - 1:
            out.append(nums[window[0]])
    return out''', [(([1, 3, -1, -3, 5, 3, 6, 7], 3), [-1, -3, -3, -3, 3, 3]), (([4], 1), [4])], [([1, 2, 3], 3), ([3, 2, 1], 1), ([2, 2, 2, 2], 2), ([5, 1, 4, 2, 3], 2)])

U = "linked-lists"
linked("largest-value-in-a-linked-list", "Largest Value in a Linked List", U, "easy", "Traversal", "Write `max_value(head)` returning the largest value in a non-empty linked list.",
       "def max_value(head):\n    best = head.val\n    while head is not None:\n        best = max(best, head.val)\n        head = head.next\n    return best",
       "max_value(build_list({0}))", [([3, 9, 2], 9), ([-5], -5)], [[1, 2, 3], [3, 2, 1], [0, 0], [-3, -1, -2], [7, 7, 8, 7]])
linked("count-a-value-in-a-linked-list", "Count a Value in a Linked List", U, "easy", "Traversal", "Write `count_value(head, x)` counting the nodes whose value is x.",
       "def count_value(head, x):\n    count = 0\n    while head is not None:\n        count += head.val == x\n        head = head.next\n    return count",
       "count_value(build_list({0}), {1})", [(([1, 2, 1, 1], 1), 3), (([], 5), 0)], [([5], 5), ([5], 4), ([2, 2, 2], 2), ([1, 2, 3], 4)])
linked("insert-at-a-position", "Insert at a Position", U, "medium", "Pointer rewiring",
       "Write `insert_at(head, index, value)` adding a new node holding `value` so that it ends up at position `index`, counting from 0, and return the head. index is between 0 and the length of the list. A dummy node in front makes inserting at the start work like anywhere else.",
       '''def insert_at(head, index, value):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(index):
        prev = prev.next
    prev.next = ListNode(value, prev.next)
    return dummy.next''', "to_list(insert_at(build_list({0}), {1}, {2}))", [(([1, 2, 3], 1, 9), [1, 9, 2, 3]), (([], 0, 5), [5])],
       [([1], 0, 0), ([1], 1, 0), ([1, 2, 3], 3, 4), ([4, 5], 0, 3), ([7, 8, 9], 2, 1)])
linked("delete-the-middle-node", "Delete the Middle Node", U, "medium", "Fast and slow pointers",
       "Write `delete_middle(head)` removing the node at position `length // 2`, counting from 0, and returning the head. A list of one node becomes empty. Move one pointer two steps for every one step of another, so the slow one stops just before the middle.",
       '''def delete_middle(head):
    if head is None or head.next is None:
        return None
    slow, fast = head, head.next.next
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
    slow.next = slow.next.next
    return head''', "to_list(delete_middle(build_list({0})))", [([1, 2, 3, 4], [1, 2, 4]), ([1], [])], [[], [1, 2], [1, 2, 3], [1, 2, 3, 4, 5], [9, 8, 7, 6, 5, 4]])
linked("weave-two-lists", "Weave Two Lists", U, "medium", "Merging and dummy heads",
       "Write `weave(a, b)` joining two linked lists by taking nodes in turn, first from a, then from b. When one list runs out, the rest of the other follows. A dummy head gives the new list somewhere to start.",
       '''def weave(a, b):
    dummy = tail = ListNode()
    while a is not None and b is not None:
        tail.next, a = a, a.next
        tail = tail.next
        tail.next, b = b, b.next
        tail = tail.next
    tail.next = a if a is not None else b
    return dummy.next''', "to_list(weave(build_list({0}), build_list({1})))", [(([1, 3, 5], [2, 4]), [1, 2, 3, 4, 5]), (([], [7]), [7])],
       [([], []), ([1], []), ([1, 2, 3], [9]), ([1], [2, 3, 4]), ([5, 5], [6, 6])])
linked("remove-repeats-from-unsorted-list", "Remove Repeats From an Unsorted List", U, "medium", "Pointer rewiring",
       "Write `remove_repeats(head)` keeping only the first node holding each value, and returning the head. The list is not sorted, so remember the values already seen and link past the nodes that repeat them.",
       '''def remove_repeats(head):
    seen = set()
    prev, node = None, head
    while node is not None:
        if node.val in seen:
            prev.next = node.next
        else:
            seen.add(node.val)
            prev = node
        node = node.next
    return head''', "to_list(remove_repeats(build_list({0})))", [([3, 1, 3, 2, 1], [3, 1, 2]), ([], [])], [[1], [1, 1, 1], [1, 2, 3], [2, 1, 2, 1, 2], [5, 4, 5, 4, 3]])
linked("split-a-list-in-half", "Split a List in Half", U, "medium", "Fast and slow pointers",
       "Write `halves(head)` splitting a linked list into a front half and a back half, and returning them as `[front, back]`. When the length is odd, the front half gets the extra node. Either half may be empty.",
       '''def halves(head):
    if head is None:
        return [None, None]
    slow, fast = head, head.next
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
    back = slow.next
    slow.next = None
    return [head, back]''', "[to_list(part) for part in halves(build_list({0}))]", [([1, 2, 3, 4, 5], [[1, 2, 3], [4, 5]]), ([], [[], []])], [[1], [1, 2], [1, 2, 3, 4], [9, 8, 7, 6, 5, 4]])

U = "trees"
tree("largest-value-in-a-tree", "Largest Value in a Tree", U, "easy", "Depth-first traversal", "Write `tree_max(root)` returning the largest value in a non-empty binary tree.",
     '''def tree_max(root):
    best = root.val
    for child in (root.left, root.right):
        if child is not None:
            best = max(best, tree_max(child))
    return best''', "tree_max(build_tree({0}))", [([3, 9, 20, None, None, 15, 7], 20), ([-4], -4)], [[1, 2, 3], [5, None, 9, None, 1], [0, -1, -2], [2, 8, 3, None, 10]])
tree("total-of-each-level", "Total of Each Level", U, "easy", "Breadth-first traversal",
     "Write `level_sums(root)` returning the total of the values on each level, from the root down. An empty tree gives an empty list.",
     '''def level_sums(root):
    out, level = [], [root] if root else []
    while level:
        out.append(sum(node.val for node in level))
        level = [child for node in level for child in (node.left, node.right) if child]
    return out''', "level_sums(build_tree({0}))", [([1, 2, 3, 4, 5], [1, 5, 9]), ([], [])], [[7], [1, None, 2, None, 3], [5, -5, 5], [1, 2, 3, 4, 5, 6, 7, 8]])
tree("shallowest-leaf", "Shallowest Leaf", U, "easy", "Tree properties",
     "Write `min_depth(root)` returning how many nodes are on the shortest path from the root down to a leaf, which is a node with no children. An empty tree has depth 0. A node with one child is not a leaf, so only follow the side that exists.",
     '''def min_depth(root):
    if root is None:
        return 0
    if root.left is None:
        return 1 + min_depth(root.right)
    if root.right is None:
        return 1 + min_depth(root.left)
    return 1 + min(min_depth(root.left), min_depth(root.right))''', "min_depth(build_tree({0}))", [([3, 9, 20, None, None, 15, 7], 2), ([1, None, 2], 2)],
     [[], [1], [1, 2, 3, 4], [1, 2, None, 3, None, 4], [1, 2, 3, None, None, 4, 5]])
tree("total-within-a-range", "Total Within a Range", U, "medium", "Binary search trees",
     "Write `range_total(root, low, high)` adding up the values in a binary search tree that lie between low and high, inclusive. low is never above high. Skip a whole side of the tree when it cannot hold values in range.",
     '''def range_total(root, low, high):
    if root is None:
        return 0
    if root.val < low:
        return range_total(root.right, low, high)
    if root.val > high:
        return range_total(root.left, low, high)
    return root.val + range_total(root.left, low, high) + range_total(root.right, low, high)''', "range_total(build_tree({0}), {1}, {2})",
     [(([10, 5, 15, 3, 7, None, 18], 7, 15), 32), (([], 1, 5), 0)], [([5], 5, 5), ([5], 6, 9), ([4, 2, 6, 1, 3, 5, 7], 1, 7), ([4, 2, 6, 1, 3, 5, 7], 3, 5), ([8, 3, 10, 1, 6, None, 14], 4, 11)])
tree("best-root-to-leaf-total", "Best Root-to-Leaf Total", U, "medium", "Path problems",
     "Write `best_path(root)` returning the largest total of the values on any path from the root down to a leaf, for a non-empty tree. Values may be negative, so a path must end at a real leaf.",
     '''def best_path(root):
    if root.left is None and root.right is None:
        return root.val
    return root.val + max(best_path(child) for child in (root.left, root.right) if child is not None)''', "best_path(build_tree({0}))",
     [([1, 2, 3], 4), ([5, -10, None, 1], -4)], [[7], [1, -2, -3], [10, None, -1, None, -1], [1, 2, 3, 4, None, None, -100], [-5, -1, -2]])
tree("nodes-with-no-larger-ancestor", "Nodes With No Larger Ancestor", U, "medium", "Path problems",
     "Write `good_nodes(root)` counting nodes whose value is at least as large as every value on the path from the root down to them. The root always counts, and an empty tree has none. Pass the largest value seen so far down the tree.",
     '''def good_nodes(root):
    def walk(node, best):
        if node is None:
            return 0
        here = 1 if node.val >= best else 0
        best = max(best, node.val)
        return here + walk(node.left, best) + walk(node.right, best)
    return walk(root, float("-inf"))''', "good_nodes(build_tree({0}))", [([3, 1, 4, 3, None, 1, 5], 4), ([], 0)],
     [[1], [3, 3, None, 4, 2], [2, None, 4, 10, 8, None, None, 4], [5, 4, 3, 2, 1], [1, 2, 3, 4, 5]])
tree("smallest-gap-in-a-search-tree", "Smallest Gap in a Search Tree", U, "medium", "Binary search trees",
     "Write `min_gap(root)` returning the smallest difference between any two values in a binary search tree with at least two nodes. An in-order walk visits the values in sorted order, so only neighbours in that order need comparing.",
     '''def min_gap(root):
    values = []
    def walk(node):
        if node is None:
            return
        walk(node.left)
        values.append(node.val)
        walk(node.right)
    walk(root)
    return min(b - a for a, b in zip(values, values[1:]))''', "min_gap(build_tree({0}))", [([4, 2, 6, 1, 3], 1), ([10, 5, 20], 5)],
     [[1, None, 3], [50, 20, 90, None, 30], [8, 3, 10, 1, 6, None, 14, None, None, 4, 7, 13]])
tree("widest-level", "Widest Level", U, "easy", "Breadth-first traversal", "Write `widest(root)` returning how many nodes the most crowded level holds. An empty tree gives 0.",
     '''def widest(root):
    best, level = 0, [root] if root else []
    while level:
        best = max(best, len(level))
        level = [child for node in level for child in (node.left, node.right) if child]
    return best''', "widest(build_tree({0}))", [([1, 2, 3, 4, 5, 6], 3), ([], 0)], [[1], [1, None, 2, None, 3], [1, 2, 3, 4, 5, 6, 7, 8], [5, 4, 8, 11, None, 13, 4, 7, 2, None, None, None, 1]])

U = "graphs"
fn("directed-adjacency-lists", "Directed Adjacency Lists", U, "easy", "Graph representation",
   "Nodes are numbered 0 to n - 1, and each edge `[a, b]` goes from a to b. Write `out_lists(n, edges)` returning, for each node, the sorted list of nodes its edges lead to.",
   '''def out_lists(n, edges):
    out = [[] for _ in range(n)]
    for a, b in edges:
        out[a].append(b)
    return [sorted(targets) for targets in out]''', [((3, [[0, 1], [0, 2], [2, 1]]), [[1, 2], [], [1]]), ((2, []), [[], []])],
   [(1, []), (4, [[3, 0], [3, 1], [3, 2]]), (3, [[0, 1], [1, 2], [2, 0]]), (4, [[1, 0], [2, 0], [0, 3]])])
fn("how-many-can-be-reached", "How Many Can Be Reached", U, "easy", "Depth-first search",
   "A graph is given as adjacency lists, where `graph[i]` lists the nodes you can go to from node i. Write `reachable(graph, start)` counting the nodes you can reach from start, including start itself. Mark nodes as seen so none is counted twice.",
   '''def reachable(graph, start):
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen)''', [(([[1], [2], [], [0]], 0), 3), (([[], [0]], 0), 1)],
   [([[]], 0), ([[1], [0]], 1), ([[1, 2], [3], [3], []], 0), ([[1], [2], [0], []], 3), ([[2], [], [1], [4], []], 0)])
fn("island-coastline", "Island Coastline", U, "easy", "Grids as graphs",
   "A non-empty grid holds 1 for land and 0 for water. Write `coastline(grid)` returning the total length of coast: every side of a land cell that faces water or the edge of the grid counts 1.",
   '''def coastline(grid):
    rows, cols = len(grid), len(grid[0])
    total = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < rows and 0 <= nc < cols) or grid[nr][nc] == 0:
                        total += 1
    return total''', [([[0, 1, 0, 0], [1, 1, 1, 0], [0, 1, 0, 0], [1, 1, 0, 0]], 16), ([[1]], 4)],
   [[[0]], [[1, 1]], [[1, 1], [1, 1]], [[1, 0, 1]], [[0, 1, 0], [1, 1, 1], [0, 1, 0]]])
fn("fewest-knight-moves", "Fewest Knight Moves", U, "medium", "Breadth-first search",
   "A chess knight moves two squares in one direction and then one square at a right angle. Write `knight_moves(n, start, end)` returning the fewest moves it needs to go from `start` to `end` on an n by n board, where squares are `[row, column]` counted from 0. Return -1 if it can never get there. Breadth-first search finds the fewest moves.",
   '''from collections import deque

def knight_moves(n, start, end):
    start, end = tuple(start), tuple(end)
    steps = {start: 0}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        if (r, c) == end:
            return steps[(r, c)]
        for dr, dc in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
            nxt = (r + dr, c + dc)
            if 0 <= nxt[0] < n and 0 <= nxt[1] < n and nxt not in steps:
                steps[nxt] = steps[(r, c)] + 1
                queue.append(nxt)
    return -1''', [((8, [0, 0], [7, 7]), 6), ((3, [0, 0], [1, 1]), -1)],
   [(1, [0, 0], [0, 0]), (5, [0, 0], [4, 4]), (8, [3, 3], [4, 3]), (4, [0, 0], [3, 3]), (8, [0, 0], [1, 2]), (2, [0, 0], [1, 1])])
fn("fewest-terms-to-finish", "Fewest Terms to Finish", U, "medium", "Topological order",
   "Courses are numbered 0 to n - 1, and each rule `[a, b]` means course b must be finished before course a. In one term you may take any number of courses whose earlier courses are done. Write `terms(n, rules)` returning the fewest terms needed to finish every course. The rules never form a loop. Take every course that is ready, term by term.",
   '''def terms(n, rules):
    after = [[] for _ in range(n)]
    needs = [0] * n
    for a, b in rules:
        after[b].append(a)
        needs[a] += 1
    current = [c for c in range(n) if needs[c] == 0]
    count = 0
    while current:
        count += 1
        following = []
        for course in current:
            for nxt in after[course]:
                needs[nxt] -= 1
                if needs[nxt] == 0:
                    following.append(nxt)
        current = following
    return count''', [((3, [[1, 0], [2, 1]]), 3), ((3, []), 1)],
   [(1, []), (4, [[1, 0], [2, 0], [3, 1], [3, 2]]), (5, [[4, 0], [4, 1], [4, 2], [4, 3]]), (6, [[1, 0], [2, 1], [5, 4]])])
fn("is-it-a-tree", "Is It a Tree?", U, "medium", "Depth-first search",
   "An undirected graph has nodes 0 to n - 1, with n at least 1, and the given edges, none repeated. Write `is_tree(n, edges)` returning True when the graph is connected and has no loop. A tree with n nodes always has exactly n - 1 edges, so check that, then check every node can be reached.",
   '''def is_tree(n, edges):
    if len(edges) != n - 1:
        return False
    graph = [[] for _ in range(n)]
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    seen = {0}
    stack = [0]
    while stack:
        node = stack.pop()
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == n''', [((5, [[0, 1], [0, 2], [0, 3], [1, 4]]), True), ((5, [[0, 1], [1, 2], [2, 3], [1, 3], [1, 4]]), False)],
   [(1, []), (2, []), (2, [[0, 1]]), (4, [[0, 1], [2, 3], [1, 2]]), (4, [[0, 1], [1, 2], [2, 0]]), (3, [[0, 1]])])
fn("groups-from-a-friendship-table", "Groups From a Friendship Table", U, "medium", "Graph representation",
   "A table records who knows whom: `table[i][j]` is 1 when person i and person j know each other. The table is symmetric, with 1 on its diagonal. A group is everyone linked through people they know. Write `groups(table)` counting the groups.",
   '''def groups(table):
    n = len(table)
    seen = set()
    count = 0
    for person in range(n):
        if person in seen:
            continue
        count += 1
        stack = [person]
        seen.add(person)
        while stack:
            current = stack.pop()
            for other in range(n):
                if table[current][other] == 1 and other not in seen:
                    seen.add(other)
                    stack.append(other)
    return count''', [([[1, 1, 0], [1, 1, 0], [0, 0, 1]], 2), ([[1, 0], [0, 1]], 2)],
   [[[1]], [[1, 1], [1, 1]], [[1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 1, 1], [1, 0, 1, 1]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]])
