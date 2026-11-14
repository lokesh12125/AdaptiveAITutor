"""More problems for recursion, searching and sorting, arrays and two pointers, and hashing."""
from dsl import fn

U = "recursion"
fn("binary-digits-recursively", "Binary Digits Recursively", U, "easy", "Linear recursion",
   'Write `to_binary(n)` returning the binary digits of a non-negative number as text, recursively, with no loop and without `bin`. `to_binary(0)` is `"0"`.',
   "def to_binary(n):\n    if n < 2:\n        return str(n)\n    return to_binary(n // 2) + str(n % 2)", [(5, "101"), (0, "0")], [1, 2, 8, 255, 1024, 37])
fn("sum-a-list-recursively", "Sum a List Recursively", U, "easy", "Recursion on sequences",
   "Write `rec_sum(items)` adding up a list recursively: the first item plus the sum of the rest. The sum of an empty list is 0.",
   "def rec_sum(items):\n    if not items:\n        return 0\n    return items[0] + rec_sum(items[1:])", [([1, 2, 3], 6), ([], 0)], [[5], [-1, 1], [10, 20, 30, 40], [0, 0, 0]])
fn("search-sorted-recursively", "Search a Sorted List Recursively", U, "medium", "Divide and conquer",
   "Write `contains(nums, x)` for a sorted list, returning True if x is in it. Look at the middle item, then search only the half that could hold x, recursively.",
   '''def contains(nums, x):
    if not nums:
        return False
    mid = len(nums) // 2
    if nums[mid] == x:
        return True
    if nums[mid] < x:
        return contains(nums[mid + 1:], x)
    return contains(nums[:mid], x)''', [(([1, 3, 5, 7], 5), True), (([1, 3, 5, 7], 4), False)],
   [([], 1), ([2], 2), ([2], 3), ([1, 2, 3, 4, 5, 6], 6), ([1, 2, 3, 4, 5, 6], 1), ([-5, 0, 5], 0)])
fn("all-bit-strings", "All Bit Strings", U, "medium", "Backtracking",
   "Write `bit_strings(n)` returning every string of n characters made of `0` and `1`, in sorted order. Build each string one character at a time, trying `0` and then `1`.",
   '''def bit_strings(n):
    out = []
    def walk(text):
        if len(text) == n:
            out.append(text)
            return
        walk(text + "0")
        walk(text + "1")
    walk("")
    return out''', [(2, ["00", "01", "10", "11"]), (0, [""])], [1, 3, 4, 5])
fn("subsets-with-a-target-sum", "Subsets With a Target Sum", U, "hard", "Backtracking",
   "Write `subsets_summing(nums, target)` returning every subset of `nums`, a list of different positive numbers, that adds up to `target`. Keep each subset's numbers in their original order, and return the subsets sorted. Stop going deeper once the total passes the target.",
   '''def subsets_summing(nums, target):
    out = []
    def walk(i, chosen, left):
        if left == 0:
            out.append(chosen)
            return
        if i == len(nums) or left < 0:
            return
        walk(i + 1, chosen + [nums[i]], left - nums[i])
        walk(i + 1, chosen, left)
    walk(0, [], target)
    return sorted(out)''', [(([1, 2, 3, 4], 5), [[1, 4], [2, 3]]), (([5], 3), [])], [([], 0), ([1, 2, 3], 6), ([2, 4, 6, 8], 10), ([3, 1, 2], 3), ([10, 20], 0)])
fn("count-a-digit-recursively", "Count a Digit Recursively", U, "easy", "Linear recursion",
   "Write `count_digit(n, d)` counting how many times the digit d appears in the non-negative number n, recursively. The number 0 contains one 0.",
   '''def count_digit(n, d):
    here = 1 if n % 10 == d else 0
    if n < 10:
        return here
    return here + count_digit(n // 10, d)''', [((1231, 1), 2), ((0, 0), 1)], [(5, 5), (5, 4), (1000, 0), (999, 9), (123456789, 7)])
fn("row-of-pascals-triangle", "Row of Pascal's Triangle", U, "medium", "Linear recursion",
   "Write `pascal_row(n)` returning row n of Pascal's triangle, counting from row 0, which is `[1]`. Each row starts and ends with 1, and each number in between is the sum of the two above it. Build it from row n - 1, recursively.",
   '''def pascal_row(n):
    if n == 0:
        return [1]
    above = pascal_row(n - 1)
    return [1] + [above[i] + above[i + 1] for i in range(len(above) - 1)] + [1]''', [(0, [1]), (3, [1, 3, 3, 1])], [1, 2, 4, 6, 10])

U = "searching-sorting"
fn("top-of-the-mountain", "Top of the Mountain", U, "medium", "Linear and binary search",
   "A list rises strictly to one highest value and then falls strictly. Either part may be empty. Write `peak_index(nums)` returning the position of the highest value in about log n steps. If the middle item is lower than the next one, the peak is to its right.",
   '''def peak_index(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < nums[mid + 1]:
            lo = mid + 1
        else:
            hi = mid
    return lo''', [([1, 3, 5, 4, 2], 2), ([0, 10, 5], 1)], [[7], [1, 2], [2, 1], [1, 2, 3, 4, 5], [9, 7, 5, 3], [0, 2, 4, 6, 5, 3, 1]])
fn("closest-value-in-sorted-list", "Closest Value in a Sorted List", U, "medium", "Linear and binary search",
   "Write `closest(nums, x)` for a non-empty sorted list, returning the value nearest to x. When two values are equally near, return the smaller. Binary search finds where x would go, and then only its two neighbours need comparing.",
   '''from bisect import bisect_left

def closest(nums, x):
    i = bisect_left(nums, x)
    if i == 0:
        return nums[0]
    if i == len(nums):
        return nums[-1]
    before, after = nums[i - 1], nums[i]
    return before if x - before <= after - x else after''', [(([1, 4, 7, 10], 6), 7), (([1, 3, 5], 4), 3)],
   [([5], 100), ([5], -100), ([1, 2, 3], 2), ([-10, 0, 10], -4), ([2, 4, 6, 8], 9), ([1, 1, 2], 1)])
fn("fairest-split", "Fairest Split", U, "hard", "Binary search on answers",
   "Write `min_largest(nums, k)` splitting a list of non-negative numbers into k non-empty stretches of neighbours, so that the largest stretch total is as small as possible, and return that total. k is between 1 and the length of the list. Binary search on the answer: for a guess, count how many stretches you need if none may go over it.",
   '''def min_largest(nums, k):
    lo, hi = max(nums), sum(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        parts, total = 1, 0
        for n in nums:
            if total + n > mid:
                parts += 1
                total = 0
            total += n
        if parts <= k:
            hi = mid
        else:
            lo = mid + 1
    return lo''', [(([7, 2, 5, 10, 8], 2), 18), (([1, 2, 3, 4, 5], 2), 9)],
   [([5], 1), ([1, 1, 1, 1], 4), ([1, 4, 4], 3), ([2, 3, 1, 2, 4, 3], 3), ([0, 0, 0], 2), ([10, 5, 13, 4, 8, 4, 5, 11, 14, 9, 16, 10, 20, 8], 8)])
fn("swaps-in-bubble-sort", "Swaps in Bubble Sort", U, "medium", "Sorting algorithms",
   "Bubble sort swaps neighbours that are out of order until the list is sorted. Write `bubble_swaps(nums)` returning how many swaps it makes. Run the sort on a copy and count each swap.",
   '''def bubble_swaps(nums):
    out = nums[:]
    swaps = 0
    for end in range(len(out) - 1, 0, -1):
        for i in range(end):
            if out[i] > out[i + 1]:
                out[i], out[i + 1] = out[i + 1], out[i]
                swaps += 1
    return swaps''', [([3, 1, 2], 2), ([1, 2, 3], 0)], [[], [1], [2, 1], [5, 4, 3, 2, 1], [2, 2, 1], [1, 3, 2, 4]])
fn("sort-by-frequency", "Sort by Frequency", U, "medium", "Custom sort keys",
   "Write `by_frequency(nums)` sorting so the most common values come first, with repeats kept together. Values that appear equally often go from smallest to largest.",
   '''from collections import Counter

def by_frequency(nums):
    counts = Counter(nums)
    return sorted(nums, key=lambda n: (-counts[n], n))''', [([1, 2, 2, 3, 3, 3], [3, 3, 3, 2, 2, 1]), ([], [])], [[5], [4, 4, 1, 1], [2, 1, 2, 1, 3], [9, 8, 7], [0, 0, -1]])
fn("evens-before-odds", "Evens Before Odds", U, "easy", "Merge and partition",
   "Write `evens_first(nums)` returning the even numbers in their original order, followed by the odd numbers in their original order.",
   "def evens_first(nums):\n    return [n for n in nums if n % 2 == 0] + [n for n in nums if n % 2 != 0]", [([3, 2, 1, 4], [2, 4, 3, 1]), ([], [])], [[1], [2], [1, 3, 5], [2, 4, 6], [0, -1, -2, 7]])
fn("order-people-by-age", "Order People by Age", U, "easy", "Custom sort keys",
   "Write `order_people(people)`, where each person is `[name, age]`. Return the names from youngest to oldest, with people of the same age in alphabetical order.",
   "def order_people(people):\n    return [name for name, age in sorted(people, key=lambda p: (p[1], p[0]))]",
   [([["bo", 30], ["al", 25], ["cy", 30]], ["al", "bo", "cy"]), ([], [])], [[["x", 1]], [["b", 2], ["a", 2]], [["zed", 9], ["amy", 40], ["kim", 9]]])

U = "arrays-two-pointers"
fn("pair-sum-closest-to-target", "Pair Sum Closest to Target", U, "medium", "Two pointers from both ends",
   "Write `closest_sum(nums, target)` for a sorted list of at least two numbers. Return the total of two numbers at different positions whose total is closest to target. When two totals are equally close, return the smaller. Start with a pointer at each end.",
   '''def closest_sum(nums, target):
    i, j = 0, len(nums) - 1
    best = nums[i] + nums[j]
    while i < j:
        total = nums[i] + nums[j]
        gap, best_gap = abs(total - target), abs(best - target)
        if gap < best_gap or (gap == best_gap and total < best):
            best = total
        if total < target:
            i += 1
        elif total > target:
            j -= 1
        else:
            return total
    return best''', [(([1, 2, 4, 8], 7), 6), (([-3, 0, 5], 1), 2)], [([1, 1], 0), ([1, 4, 6], 6), ([0, 0, 0], 1), ([-5, -2, 3, 9], 0), ([1, 2, 3, 4, 5], 100), ([10, 20], -5)])
fn("greatest-on-the-right", "Greatest on the Right", U, "easy", "In-place updates",
   "Write `greatest_to_right(nums)` for a list of non-negative numbers, returning a copy where each item is replaced by the largest item to its right, and the last item by -1. Walk from the right, keeping the largest value seen so far.",
   '''def greatest_to_right(nums):
    out = nums[:]
    best = -1
    for i in range(len(out) - 1, -1, -1):
        out[i], best = best, max(best, out[i])
    return out''', [([17, 18, 5, 4, 6, 1], [18, 6, 6, 6, 1, -1]), ([], [])], [[5], [1, 2, 3], [3, 2, 1], [0, 0], [4, 9, 2, 9]])
fn("many-trades", "Many Trades", U, "easy", "Kadane and running best",
   "Prices are listed day by day. You may buy and sell as often as you like, holding at most one item at a time. Write `total_gain(prices)` returning the most profit possible. Every rise from one day to the next can be collected.",
   "def total_gain(prices):\n    return sum(max(0, prices[i] - prices[i - 1]) for i in range(1, len(prices)))", [([7, 1, 5, 3, 6, 4], 7), ([5, 4, 3], 0)],
   [[], [1], [1, 2, 3, 4, 5], [3, 3, 3], [1, 5, 2, 8]])
fn("windows-reaching-a-total", "Windows Reaching a Total", U, "medium", "Sliding window",
   "Write `count_windows(nums, k, total)` counting the stretches of exactly k neighbouring numbers whose sum is at least `total`. k is between 1 and the length of the list. Move the window one step at a time, adding the new number and removing the old one.",
   '''def count_windows(nums, k, total):
    window = sum(nums[:k])
    count = 1 if window >= total else 0
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        if window >= total:
            count += 1
    return count''', [(([2, 2, 2, 2, 5, 5, 5, 8], 3, 12), 3), (([1, 1, 1], 1, 1), 3)], [([5], 1, 5), ([5], 1, 6), ([1, 2, 3, 4], 2, 5), ([-1, -2, 3], 2, 0), ([10, 0, 10, 0], 2, 10)])
fn("stretches-divisible-by-k", "Stretches Divisible by K", U, "hard", "Prefix sums",
   "Write `count_divisible(nums, k)` counting stretches of neighbouring numbers whose total divides evenly by k, a positive number. Two running totals with the same remainder mark a stretch between them, so count running totals by remainder.",
   '''def count_divisible(nums, k):
    seen = {0: 1}
    total = count = 0
    for n in nums:
        total = (total + n) % k
        count += seen.get(total, 0)
        seen[total] = seen.get(total, 0) + 1
    return count''', [(([4, 5, 0, -2, -3, 1], 5), 7), (([5], 9), 0)], [([], 3), ([3], 3), ([1, 2, 3], 3), ([0, 0], 1), ([-1, 1], 2), ([2, 4, 6], 2)])
fn("keep-at-most-two", "Keep At Most Two of Each", U, "medium", "Fast and slow pointers",
   "Write `at_most_two(nums)` for a sorted list, returning a copy in which each value appears at most twice. Keep a write position, and only copy an item when it differs from the item two places behind the write position.",
   '''def at_most_two(nums):
    out = nums[:]
    write = 0
    for n in nums:
        if write < 2 or n != out[write - 2]:
            out[write] = n
            write += 1
    return out[:write]''', [([1, 1, 1, 2, 2, 3], [1, 1, 2, 2, 3]), ([], [])], [[1], [1, 1], [1, 1, 1, 1], [0, 0, 1, 1, 1, 1, 2, 3, 3], [5, 6, 7]])
fn("smallest-spread-of-k-values", "Smallest Spread of K Values", U, "medium", "Sliding window",
   "Write `min_spread(nums, k)` choosing k of the numbers so that the gap between the largest and smallest chosen is as small as possible, and return that gap. k is between 1 and the length of the list. After sorting, the best choice is always k neighbours, so slide a window of k.",
   '''def min_spread(nums, k):
    ordered = sorted(nums)
    return min(ordered[i + k - 1] - ordered[i] for i in range(len(ordered) - k + 1))''', [(([9, 4, 1, 7], 2), 2), (([5], 1), 0)],
   [([1, 2, 3], 3), ([10, 100, 1000], 2), ([3, 3, 3], 2), ([-5, 0, 5, 10], 3), ([1, 9, 2, 8, 3], 3)])

U = "hashing"
fn("first-character-to-repeat", "First Character to Repeat", U, "easy", "Seen sets",
   "Write `first_repeat(text)` reading left to right and returning the first character that has already been seen, or None if no character repeats.",
   '''def first_repeat(text):
    seen = set()
    for ch in text:
        if ch in seen:
            return ch
        seen.add(ch)
    return None''', [("abcba", "b"), ("abc", None)], ["", "aa", "abccba", "xyzx", "hello"])
fn("common-to-three-lists", "Common to Three Lists", U, "easy", "Seen sets",
   "Write `common_three(a, b, c)` returning, in sorted order and without repeats, the values found in all three lists.",
   "def common_three(a, b, c):\n    return sorted(set(a) & set(b) & set(c))", [(([1, 2, 3], [2, 3, 4], [3, 2, 9]), [2, 3]), (([], [1], [1]), [])],
   [([1], [1], [1]), ([1, 1, 2], [1, 2, 2], [2, 2, 1]), ([5, 6], [7, 8], [9]), ([0, -1], [-1, 0], [0])])
fn("count-the-jewels", "Count the Jewels", U, "easy", "Seen sets",
   "Each character of `jewels` is a kind of jewel. Write `count_jewels(jewels, stones)` counting how many characters of `stones` are jewels. Capital and small letters are different kinds.",
   "def count_jewels(jewels, stones):\n    kinds = set(jewels)\n    return sum(1 for s in stones if s in kinds)", [(("aA", "aAAbbbb"), 3), (("z", "ZZ"), 0)],
   [("", ""), ("abc", ""), ("a", "aaaa"), ("xyz", "axbycz"), ("B", "bBbB")])
fn("least-frequent-value", "Least Frequent Value", U, "easy", "Frequency maps",
   "Write `least_frequent(nums)` for a non-empty list, returning the value that appears the fewest times. When several values share that count, return the smallest of them.",
   '''from collections import Counter

def least_frequent(nums):
    counts = Counter(nums)
    return min(counts, key=lambda n: (counts[n], n))''', [([4, 4, 1, 1, 1, 7], 7), ([2, 1], 1)], [[5], [3, 3, 2, 2], [9, 8, 8, 9, 7, 7, 7], [0, -1, 0]])
fn("pairs-of-values-with-a-sum", "Pairs of Values With a Sum", U, "medium", "Complement lookup",
   "Write `value_pairs(nums, k)` counting the different pairs of values a ≤ b, taken from two different positions, where a + b equals k. Each pair of values counts once, however often it appears. For each value a, look up its complement k - a.",
   '''from collections import Counter

def value_pairs(nums, k):
    counts = Counter(nums)
    pairs = 0
    for a in counts:
        b = k - a
        if a < b and b in counts:
            pairs += 1
        elif a == b and counts[a] > 1:
            pairs += 1
    return pairs''', [(([1, 5, 3, 3, 3, 7], 6), 2), (([1, 1], 2), 1)], [([], 0), ([1], 2), ([2, 4, 4, 2], 6), ([0, 0, 0], 0), ([-1, 7, 3, 5, 1], 6), ([1, 2, 3, 4, 5, 6], 7)])
fn("group-by-last-letter", "Group by Last Letter", U, "easy", "Grouping by key",
   "Write `by_last_letter(words)` returning a dictionary that maps each last letter to the list of words ending in it, in their original order. Words are never empty.",
   '''def by_last_letter(words):
    groups = {}
    for word in words:
        groups.setdefault(word[-1], []).append(word)
    return groups''', [(["cat", "dog", "hat", "log"], {"t": ["cat", "hat"], "g": ["dog", "log"]}), ([], {})], [["a"], ["ab", "cb", "b"], ["one", "two", "three"]])
fn("where-rearrangements-start", "Where Rearrangements Start", U, "medium", "Frequency maps",
   "Write `rearranged_starts(text, pattern)` returning every position in text where some rearrangement of the letters of `pattern` begins. An empty pattern matches nowhere. Slide a window as long as the pattern and keep letter counts as it moves.",
   '''from collections import Counter

def rearranged_starts(text, pattern):
    k = len(pattern)
    if k == 0 or k > len(text):
        return []
    want = Counter(pattern)
    window = Counter(text[:k])
    out = [0] if window == want else []
    for i in range(k, len(text)):
        window[text[i]] += 1
        window[text[i - k]] -= 1
        if window[text[i - k]] == 0:
            del window[text[i - k]]
        if window == want:
            out.append(i - k + 1)
    return out''', [(("cbaebabacd", "abc"), [0, 6]), (("abab", "ab"), [0, 1, 2])], [("", "a"), ("a", ""), ("aaaa", "aa"), ("abc", "d"), ("baa", "aa"), ("xyz", "zyx")])
