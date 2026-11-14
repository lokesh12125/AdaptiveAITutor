"""More problems for dynamic programming and the Python toolkit."""
from dsl import exprs, fn, klass

U = "dynamic-programming"
fn("steps-of-one-two-or-three", "Steps of One, Two or Three", U, "easy", "One-dimensional DP",
   "Write `ways_123(n)` counting the ways to climb n stairs taking 1, 2 or 3 steps at a time. There is one way to climb 0 stairs. The ways to reach a stair are the ways to reach each of the three stairs below it, added together.",
   '''def ways_123(n):
    ways = [1, 1, 2]
    for i in range(3, n + 1):
        ways.append(ways[i - 1] + ways[i - 2] + ways[i - 3])
    return ways[n]''', [(4, 7), (0, 1)], [1, 2, 3, 10, 20, 30])
fn("fewest-perfect-squares", "Fewest Perfect Squares", U, "medium", "One-dimensional DP",
   "Write `fewest_squares(n)` returning the smallest count of perfect squares (1, 4, 9, ...) that add up to n. Zero needs none. Work out the answer for every number from 1 up to n, each from smaller answers.",
   '''def fewest_squares(n):
    best = [0] + [n] * n
    for total in range(1, n + 1):
        root = 1
        while root * root <= total:
            best[total] = min(best[total], best[total - root * root] + 1)
            root += 1
    return best[n]''', [(12, 3), (13, 2)], [0, 1, 2, 3, 4, 7, 100, 99])
fn("cheapest-path-down-a-triangle", "Cheapest Path Down a Triangle", U, "medium", "Two-dimensional grids",
   "A triangle is given as rows, where row i has i + 1 numbers. From the top, each step goes down to one of the two numbers just below. Write `triangle_min(rows)` returning the smallest total of a path from top to bottom, for a non-empty triangle. Working up from the bottom row keeps it simple.",
   '''def triangle_min(rows):
    best = rows[-1][:]
    for row in reversed(rows[:-1]):
        best = [value + min(best[i], best[i + 1]) for i, value in enumerate(row)]
    return best[0]''', [([[2], [3, 4], [6, 5, 7], [4, 1, 8, 3]], 11), ([[-10]], -10)],
   [[[1], [2, 3]], [[1], [1, 1], [1, 1, 1]], [[5], [9, 6], [4, 6, 8], [0, 7, 1, 5]], [[0], [-1, 2], [3, -4, 5]]])
fn("longest-shared-stretch-of-text", "Longest Shared Stretch of Text", U, "medium", "Strings and sequences",
   "Write `shared_length(a, b)` returning the length of the longest stretch of neighbouring characters that appears in both strings. Keep a table where each cell holds the length of the matching stretch ending at those two positions.",
   '''def shared_length(a, b):
    best = 0
    above = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        row = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                row[j] = above[j - 1] + 1
                best = max(best, row[j])
        above = row
    return best''', [(("abcde", "xbcdy"), 3), (("abc", "xyz"), 0)], [("", ""), ("a", "a"), ("aaaa", "aa"), ("banana", "ananas"), ("abcab", "cabca")])
fn("count-palindromic-stretches", "Count Palindromic Stretches", U, "medium", "Strings and sequences",
   'Write `count_pals(text)` counting the stretches of text that read the same backwards, counting each position separately, so `"aaa"` has 6. Grow outwards from every centre, both on a character and between two characters.',
   '''def count_pals(text):
    count = 0
    for centre in range(2 * len(text) - 1):
        left, right = centre // 2, centre // 2 + centre % 2
        while left >= 0 and right < len(text) and text[left] == text[right]:
            count += 1
            left -= 1
            right += 1
    return count''', [("aaa", 6), ("abc", 3)], ["", "a", "abba", "racecar", "abab"])
fn("closest-split-into-two-groups", "Closest Split Into Two Groups", U, "hard", "Choices and subsets",
   "Write `min_split_gap(nums)` dividing a list of non-negative numbers into two groups, each number going into exactly one group, and returning the smallest possible difference between the two group totals. Work out every total one group can reach.",
   '''def min_split_gap(nums):
    total = sum(nums)
    reachable = {0}
    for n in nums:
        reachable |= {r + n for r in reachable}
    return min(abs(total - 2 * r) for r in reachable)''', [([1, 6, 11, 5], 1), ([], 0)], [[3], [1, 1], [1, 2, 3, 4], [10, 20, 15, 5, 25], [2, 2, 2, 2, 1]])
fn("bit-strings-without-neighbouring-ones", "Bit Strings Without Neighbouring Ones", U, "medium", "Memoisation",
   "Write `no_double_ones(n)` counting the strings of n bits that never have two 1s side by side. Remember answers already worked out, for example with `functools.cache`, so each one is found only once.",
   '''from functools import cache

def no_double_ones(n):
    @cache
    def count(length, last_was_one):
        if length == 0:
            return 1
        total = count(length - 1, False)
        if not last_was_one:
            total += count(length - 1, True)
        return total
    return count(n, False)''', [(3, 5), (0, 1)], [1, 2, 4, 10, 30, 50])
fn("grid-paths-with-diagonal-steps", "Grid Paths With Diagonal Steps", U, "medium", "Memoisation",
   "Write `paths(rows, cols)` counting the ways to go from the top-left cell to the bottom-right cell of a grid, where each step moves one cell right, one cell down, or one cell diagonally down and right. Remember the answer for each cell so it is worked out once.",
   '''from functools import cache

def paths(rows, cols):
    @cache
    def ways(r, c):
        if r == 0 or c == 0:
            return 1
        return ways(r - 1, c) + ways(r, c - 1) + ways(r - 1, c - 1)
    return ways(rows - 1, cols - 1)''', [((2, 2), 3), ((1, 5), 1)], [(1, 1), (3, 3), (2, 3), (4, 4), (5, 7)])

U = "python-toolkit"
klass("temperature-converter-class", "Temperature Converter Class", U, "easy", "Classes and objects",
      "Write a class `Temperature` made from a value in degrees Celsius, which it keeps as `celsius`. Give it two methods: `to_fahrenheit()`, returning celsius × 9 / 5 + 32, and `to_kelvin()`, returning celsius + 273.15.",
      '''class Temperature:
    def __init__(self, celsius):
        self.celsius = celsius

    def to_fahrenheit(self):
        return self.celsius * 9 / 5 + 32

    def to_kelvin(self):
        return self.celsius + 273.15''', '''class Temperature:
    def __init__(self, celsius):
        pass

    def to_fahrenheit(self):
        pass

    def to_kelvin(self):
        pass''', [("t = Temperature(100)", "t.to_fahrenheit()", 212.0), ("t = Temperature(0)", "t.to_kelvin()", 273.15)],
      [("t = Temperature(-40)", "t.to_fahrenheit()"), ("t = Temperature(37)", "t.to_fahrenheit()"), ("t = Temperature(-273.15)", "t.to_kelvin()"), ("t = Temperature(25)", "t.celsius"),
       ("a = Temperature(10); b = Temperature(20)", "a.to_kelvin() + b.to_kelvin()"), ("t = Temperature(0)", "t.to_fahrenheit()"), ("t = Temperature(1.5)", "t.to_kelvin()"),
       ("t = Temperature(30); t.celsius = 0", "t.to_fahrenheit()"), ("t = Temperature(-10)", "round(t.to_fahrenheit(), 2)"), ("t = Temperature(100)", "t.to_kelvin()")])
klass("build-a-stack-class", "Build a Stack Class", U, "easy", "Classes and objects",
      "Write a class `Stack` with `push(x)`; `pop()`, which removes and returns the top item, or returns None when the stack is empty; `peek()`, which returns the top item without removing it, or None; and `size()`. Each stack keeps its own items.",
      '''class Stack:
    def __init__(self):
        self.items = []

    def push(self, x):
        self.items.append(x)

    def pop(self):
        return self.items.pop() if self.items else None

    def peek(self):
        return self.items[-1] if self.items else None

    def size(self):
        return len(self.items)''', '''class Stack:
    def __init__(self):
        pass

    def push(self, x):
        pass

    def pop(self):
        pass

    def peek(self):
        pass

    def size(self):
        pass''', [("s = Stack(); s.push(1); s.push(2)", "s.pop()", 2), ("s = Stack()", "s.pop()", None)],
      [("s = Stack()", "s.size()"), ("s = Stack(); s.push('a')", "s.peek()"), ("s = Stack(); s.push('a'); s.peek()", "s.size()"), ("s = Stack(); s.push(1); s.push(2); s.pop()", "s.peek()"),
       ("s = Stack()", "s.peek()"), ("s = Stack()\nfor i in range(5):\n    s.push(i)", "[s.pop() for _ in range(6)]"), ("a = Stack(); b = Stack(); a.push(1)", "b.size()"),
       ("s = Stack(); s.push(None); s.push(3); s.pop()", "s.size()"), ("s = Stack(); s.push(1); s.pop(); s.pop()", "s.size()"), ("s = Stack(); s.push([1, 2])", "s.pop()")])
klass("shopping-cart-class", "Shopping Cart Class", U, "medium", "Classes and objects",
      "Write a class `Cart` with `add(item, price, quantity=1)`, which adds that many of an item at that price each; `remove(item)`, which takes the item out completely and does nothing if it is not there; and `total()`, which returns the cost of everything in the cart. Adding an item that is already there adds to its quantity and uses the newest price.",
      '''class Cart:
    def __init__(self):
        self.items = {}

    def add(self, item, price, quantity=1):
        held = self.items.get(item, (0, 0))[1]
        self.items[item] = (price, held + quantity)

    def remove(self, item):
        self.items.pop(item, None)

    def total(self):
        return sum(price * quantity for price, quantity in self.items.values())''', '''class Cart:
    def __init__(self):
        pass

    def add(self, item, price, quantity=1):
        pass

    def remove(self, item):
        pass

    def total(self):
        pass''', [("c = Cart(); c.add('tea', 3, 2); c.add('jam', 5)", "c.total()", 11), ("c = Cart()", "c.total()", 0)],
      [("c = Cart(); c.add('tea', 3); c.remove('tea')", "c.total()"), ("c = Cart(); c.remove('nothing')", "c.total()"), ("c = Cart(); c.add('a', 2); c.add('a', 2)", "c.total()"),
       ("c = Cart(); c.add('a', 2); c.add('a', 5)", "c.total()"), ("c = Cart(); c.add('a', 1.5, 4)", "c.total()"), ("c = Cart(); c.add('a', 1, 3); c.add('b', 10); c.remove('a')", "c.total()"),
       ("x = Cart(); y = Cart(); x.add('a', 9)", "y.total()"), ("c = Cart(); c.add('a', 0, 100)", "c.total()"), ("c = Cart(); c.add('a', 4, 0)", "c.total()"),
       ("c = Cart(); c.add('a', 2, 2); c.add('b', 3, 3); c.add('c', 4, 4)", "c.total()")])
fn("read-a-number-safely", "Read a Number Safely", U, "easy", "Errors and exceptions",
   "Write `to_int(text, default=0)` returning `int(text)`, or `default` when the text is not a whole number. Catch the ValueError that `int()` raises, rather than checking the text yourself.",
   "def to_int(text, default=0):\n    try:\n        return int(text)\n    except ValueError:\n        return default", [("42", 42), (("abc", -1), -1), ("x", 0)],
   ["-7", " 8 ", "3.5", "", ("", 99), ("12", 99), "007"])
fn("safe-item-lookup", "Safe Item Lookup", U, "easy", "Errors and exceptions",
   "Write `safe_get(items, index, default=None)` returning `items[index]`, or `default` when there is no item at that position. Negative positions count from the end, as usual. Catch the IndexError rather than checking the length.",
   "def safe_get(items, index, default=None):\n    try:\n        return items[index]\n    except IndexError:\n        return default", [(([1, 2, 3], 1), 2), (([1, 2, 3], 5), None), (([1, 2, 3], -1), 3)],
   [([], 0), ([], 0, "none"), ([9], -1), ([9], -2, 0), (["a", "b"], 1, "z"), ([4, 5], 2, -1)])
fn("check-an-age", "Check an Age", U, "medium", "Errors and exceptions",
   'Write `age_message(text)` that reads an age from text. Return `"not a number"` when `int()` cannot read it, `"too low"` when it is below 0, `"too high"` when it is above 150, and `"ok"` otherwise. Use try and except for the first case.',
   '''def age_message(text):
    try:
        age = int(text)
    except ValueError:
        return "not a number"
    if age < 0:
        return "too low"
    if age > 150:
        return "too high"
    return "ok"''', [("30", "ok"), ("abc", "not a number"), ("-1", "too low")], ["0", "150", "151", "", "12.5", "200", " 7"])
exprs("countdown-generator", "Countdown Generator", U, "easy", "Iterators and generators",
      "Write a generator function `countdown(n)` that yields n, n - 1, and so on down to 1. It yields nothing when n is 0 or less. Use `yield` rather than building a list.",
      "def countdown(n):\n    while n > 0:\n        yield n\n        n -= 1", [("list(countdown(3))", [3, 2, 1]), ("list(countdown(0))", [])],
      ["list(countdown(1))", "list(countdown(-2))", "sum(countdown(100))", "next(countdown(5))", "len(list(countdown(20)))", "type(countdown(3)).__name__",
       "[x * 2 for x in countdown(4)]", "list(countdown(10))", "max(countdown(7))", "min(countdown(9))"])
exprs("chunks-generator", "Chunks Generator", U, "medium", "Iterators and generators",
      "Write a generator function `chunks(items, size)` that yields pieces of `size` neighbouring items, in order. The last piece may be shorter. size is at least 1.",
      "def chunks(items, size):\n    for start in range(0, len(items), size):\n        yield items[start:start + size]",
      [("list(chunks([1, 2, 3, 4, 5], 2))", [[1, 2], [3, 4], [5]]), ("list(chunks([], 3))", [])],
      ["list(chunks([1], 1))", "list(chunks([1, 2, 3], 3))", "list(chunks([1, 2, 3], 5))", "list(chunks('abcdefg', 3))", "next(chunks([9, 8, 7], 2))",
       "type(chunks([1], 1)).__name__", "len(list(chunks(list(range(100)), 7)))", "[sum(c) for c in chunks([1, 2, 3, 4, 5, 6], 2)]", "list(chunks([0, 0, 0, 0], 1))",
       "list(chunks([[1], [2], [3]], 2))"])
fn("most-common-words", "Most Common Words", U, "medium", "Standard library",
   "Write `top_words(text, k)` returning the k most common words in the text, most common first, with equally common words in alphabetical order. Words are separated by spaces, and capital letters count the same as small ones. `collections.Counter` does the counting.",
   '''from collections import Counter

def top_words(text, k):
    counts = Counter(text.lower().split())
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [word for word, _ in ranked[:k]]''', [(("the cat and the hat and the bat", 2), ["the", "and"]), (("", 3), [])],
   [("a", 1), ("b a", 5), ("Go go GO stop", 1), ("x y z x y x", 3), ("one two two three three three", 0)])
fn("days-between-dates", "Days Between Dates", U, "medium", "Standard library",
   "Write `days_between(a, b)` for two dates written as `YYYY-MM-DD`, returning how many days apart they are, never negative. `datetime.date.fromisoformat` reads the text, and subtracting two dates gives a gap whose `.days` is the answer.",
   '''from datetime import date

def days_between(a, b):
    return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)''', [(("2024-01-01", "2024-03-01"), 60), (("2023-05-10", "2023-05-10"), 0)],
   [("2024-12-31", "2024-01-01"), ("2000-02-28", "2000-03-01"), ("1999-12-31", "2000-01-01"), ("2023-02-28", "2023-03-01"), ("2020-06-15", "2021-06-15")])
