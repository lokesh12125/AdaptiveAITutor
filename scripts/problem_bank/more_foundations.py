"""More problems for the first seven topics: basics, input and output, decisions, loops, functions, strings, lists and dictionaries."""
from dsl import exprs, fn, io

U = "python-basics"
io("shout-it-back", "Shout It Back", U, "easy", "First programs", "Read one line of text and print it in capitals, followed by an exclamation mark.",
   'text = input()\nprint(text.upper() + "!")', [("hello\n", "HELLO!\n"), ("Python rocks\n", "PYTHON ROCKS!\n")], ["a\n", "Mixed Case 42\n", "already LOUD\n", "x y z\n"])
io("say-it-three-times", "Say It Three Times", U, "easy", "First programs", "Read one word and print it three times on one line, with a space between each.",
   "word = input()\nprint(word, word, word)", [("hi\n", "hi hi hi\n"), ("go\n", "go go go\n")], ["a\n", "Python\n", "123\n", "ok!\n"])
fn("classify-number-text", "What Kind of Number?", U, "easy", "Values and types",
   'Write `number_kind(text)` returning `"int"` if the text is a whole number such as `"42"` or `"-7"`, `"float"` if it is a decimal number such as `"3.5"`, and `"not a number"` otherwise. `int()` and `float()` raise ValueError for text they cannot read.',
   '''def number_kind(text):
    try:
        int(text)
        return "int"
    except ValueError:
        pass
    try:
        float(text)
        return "float"
    except ValueError:
        return "not a number"''', [("42", "int"), ("3.5", "float"), ("abc", "not a number")], ["-7", "0", "-0.25", "", "12a", "1.0", "99999"])
fn("join-as-text", "Join as Text", U, "easy", "Values and types", 'Write `join_values(a, b)` that turns both values into text and joins them, so `join_values(3, 4)` is `"34"`.',
   "def join_values(a, b):\n    return str(a) + str(b)", [((3, 4), "34"), (("ab", 5), "ab5")], [(0, 0), (-1, 2), (2.5, "x"), ("", ""), (True, 1), (10, -10)])
fn("hours-to-minutes", "Hours to Minutes", U, "easy", "Simple functions", "Write `to_minutes(hours)` returning how many minutes are in that many hours.",
   "def to_minutes(hours):\n    return hours * 60", [(2, 120), (0, 0)], [1, 24, 1.5, 10, 100])
fn("average-of-two-numbers", "Average of Two Numbers", U, "easy", "Simple functions", "Write `average(a, b)` returning the value halfway between a and b.",
   "def average(a, b):\n    return (a + b) / 2", [((2, 4), 3.0), ((1, 2), 1.5)], [(0, 0), (-4, 4), (10, -3), (7, 7), (100, 1)])
fn("double-anything", "Double Anything", U, "easy", "Values and types",
   "Write `double(value)` returning `value + value`. The same `+` adds numbers, joins text, and joins lists, so `double(4)` is 8 and `double(\"ab\")` is `\"abab\"`.",
   "def double(value):\n    return value + value", [(4, 8), ("ab", "abab")], [0, -3, 2.5, "", "x", [1], [1, 2]])

U = "variables-io"
io("age-next-year", "Age Next Year", U, "easy", "Reading input", "Read a name on the first line and an age on the second. Print `<name> will be <age + 1> next year.`",
   'name = input()\nage = int(input())\nprint(f"{name} will be {age + 1} next year.")', [("Ada\n36\n", "Ada will be 37 next year.\n"), ("Bo\n0\n", "Bo will be 1 next year.\n")],
   ["Linus\n99\n", "Mei\n17\n", "Omar\n45\n", "Zoe\n8\n"])
io("total-of-one-line", "Total of One Line", U, "easy", "Reading input", "Read one line of whole numbers separated by spaces and print their total. An empty line totals 0.",
   "print(sum(int(x) for x in input().split()))", [("1 2 3\n", "6\n"), ("10 -4\n", "6\n")], ["\n", "5\n", "0 0 0\n", "100 200 300 400\n", "-1 -2 -3\n"])
fn("pad-with-zeros", "Pad With Zeros", U, "easy", "Formatting output",
   "Write `padded(n, width)` returning the non-negative number n as text, with zeros added in front until it is `width` characters long. Numbers that are already long enough stay as they are.",
   "def padded(n, width):\n    return str(n).zfill(width)", [((7, 3), "007"), ((1234, 2), "1234")], [(0, 1), (42, 5), (5, 0), (99, 2), (100, 4)])
io("percentage-score", "Percentage Score", U, "easy", "Formatting output",
   "Read a score, then the highest possible score, each on its own line. Print the score as a percentage with one decimal place and a % sign, such as `85.0%`.",
   'score = float(input())\ntotal = float(input())\nprint(f"{score / total * 100:.1f}%")', [("17\n20\n", "85.0%\n"), ("1\n3\n", "33.3%\n")], ["0\n10\n", "10\n10\n", "7\n8\n", "45\n60\n"])
fn("kilometres-to-miles", "Kilometres to Miles", U, "easy", "Arithmetic and operators", "Write `to_miles(km)` returning the distance in miles, rounded to 2 decimal places. One kilometre is 0.621371 miles.",
   "def to_miles(km):\n    return round(km * 0.621371, 2)", [(10, 6.21), (0, 0.0)], [1, 5, 42.195, 100, 3.3])
fn("tens-and-ones", "Tens and Ones", U, "easy", "Arithmetic and operators", "Write `tens_ones(n)` for a two-digit number, returning `[tens digit, ones digit]`. Use `//` and `%`.",
   "def tens_ones(n):\n    return [n // 10, n % 10]", [(47, [4, 7]), (10, [1, 0])], [99, 50, 11, 23, 86])
io("price-with-tax", "Price With Tax", U, "medium", "Formatting output", "Read a price, then a tax rate in percent, each on its own line. Print the price including tax, with exactly two decimal places.",
   'price = float(input())\nrate = float(input())\nprint(f"{price * (1 + rate / 100):.2f}")', [("100\n20\n", "120.00\n"), ("9.99\n0\n", "9.99\n")], ["50\n5\n", "0\n18\n", "19.5\n10\n", "1234.5\n7.5\n"])

U = "conditionals"
fn("old-enough-to-vote", "Old Enough to Vote", U, "easy", "Simple decisions", "Write `can_vote(age)` returning True when age is 18 or more.",
   "def can_vote(age):\n    return age >= 18", [(18, True), (17, False)], [0, 30, 100, 19, 5])
fn("larger-of-two", "Larger of Two", U, "easy", "Simple decisions", "Write `larger(a, b)` returning the larger of two numbers, without using `max`.",
   "def larger(a, b):\n    if a >= b:\n        return a\n    return b", [((3, 9), 9), ((-1, -5), -1)], [(0, 0), (2.5, 2), (100, 101), (-3, 3)])
fn("body-mass-category", "Body Mass Category", U, "easy", "Multiple branches",
   'Write `bmi_category(bmi)` returning `"under"` below 18.5, `"normal"` from 18.5 up to but not including 25, `"over"` from 25 up to but not including 30, and `"obese"` from 30.',
   '''def bmi_category(bmi):
    if bmi < 18.5:
        return "under"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "over"
    return "obese"''', [(22, "normal"), (31.5, "obese")], [18.5, 18.4, 25, 29.9, 30, 10, 24.99])
fn("season-of-the-month", "Season of the Month", U, "easy", "Multiple branches",
   'Write `season(month)` for a month number from 1 to 12, using northern seasons: 12, 1 and 2 are `"winter"`, 3 to 5 `"spring"`, 6 to 8 `"summer"`, and 9 to 11 `"autumn"`.',
   '''def season(month):
    if month in (12, 1, 2):
        return "winter"
    if month <= 5:
        return "spring"
    if month <= 8:
        return "summer"
    return "autumn"''', [(1, "winter"), (7, "summer")], [2, 3, 5, 6, 8, 9, 11, 12, 4, 10])
fn("number-in-range", "Number in Range", U, "easy", "Combined conditions", "Write `in_range(x, low, high)` returning True when x is between low and high, including both ends. low is never above high.",
   "def in_range(x, low, high):\n    return low <= x <= high", [((5, 1, 10), True), ((0, 1, 10), False)], [(1, 1, 10), (10, 1, 10), (11, 1, 10), (-5, -10, -1), (3, 3, 3), (4, 3, 3)])
fn("kind-of-triangle", "Kind of Triangle", U, "medium", "Multiple branches",
   'Write `triangle_kind(a, b, c)` for three positive side lengths. Return `"not a triangle"` if any two sides together are not longer than the third. Otherwise return `"equilateral"` when all three sides match, `"isosceles"` when exactly two match, and `"scalene"` when none do.',
   '''def triangle_kind(a, b, c):
    if a + b <= c or a + c <= b or b + c <= a:
        return "not a triangle"
    if a == b == c:
        return "equilateral"
    if a == b or b == c or a == c:
        return "isosceles"
    return "scalene"''', [((3, 3, 3), "equilateral"), ((3, 4, 5), "scalene"), ((1, 2, 3), "not a triangle")],
   [(5, 5, 8), (2, 2, 5), (7, 10, 5), (4, 4, 4), (6, 1, 6), (1, 1, 1), (10, 1, 1)])
fn("same-sign", "Same Sign", U, "easy", "Combined conditions",
   "Write `same_sign(a, b)` returning True when both numbers are positive or both are negative. Zero is neither, so any pair with a zero gives False.",
   "def same_sign(a, b):\n    return (a > 0 and b > 0) or (a < 0 and b < 0)", [((2, 5), True), ((-1, 4), False), ((0, 0), False)], [(-3, -9), (0, 5), (-2, 0), (7, 7), (1, -1)])
fn("shipping-cost", "Shipping Cost", U, "medium", "Combined conditions",
   "Write `shipping(weight, express)`. Parcels up to 1 kg cost 5, up to 5 kg cost 10, and heavier ones cost 20. When `express` is True, the price doubles.",
   '''def shipping(weight, express):
    if weight <= 1:
        cost = 5
    elif weight <= 5:
        cost = 10
    else:
        cost = 20
    if express:
        cost *= 2
    return cost''', [((0.5, False), 5), ((3, True), 20)], [(1, False), (1, True), (5, False), (5.1, False), (10, True), (2, False)])

U = "loops"
fn("product-of-a-list", "Product of a List", U, "easy", "Running totals", "Write `product(nums)` multiplying all the numbers together with a loop. The product of an empty list is 1.",
   "def product(nums):\n    total = 1\n    for n in nums:\n        total *= n\n    return total", [([2, 3, 4], 24), ([], 1)], [[5], [0, 9], [-1, -2, -3], [1, 1, 1, 1], [10, 10]])
fn("count-even-digits", "Count Even Digits", U, "easy", "Digit loops",
   "Write `even_digits(n)` counting the even digits in a non-negative whole number. The number 0 has one digit, and it is even.",
   '''def even_digits(n):
    count = 0
    while True:
        if n % 10 % 2 == 0:
            count += 1
        n //= 10
        if n == 0:
            return count''', [(2468, 4), (0, 1), (135, 0)], [7, 10, 2020, 999999, 123456])
fn("armstrong-number", "Armstrong Number", U, "medium", "Digit loops",
   "A number is an Armstrong number when its digits, each raised to the power of how many digits it has, add up to the number itself. 153 is one, since 1³ + 5³ + 3³ = 153. Write `is_armstrong(n)` for a non-negative number.",
   '''def is_armstrong(n):
    digits = len(str(n))
    total, rest = 0, n
    while rest > 0:
        total += (rest % 10) ** digits
        rest //= 10
    return total == n''', [(153, True), (10, False)], [0, 9, 370, 371, 407, 100, 9474, 9475])
fn("position-of-the-largest", "Position of the Largest", U, "easy", "Counting and searching",
   "Write `index_of_max(nums)` returning the position of the largest number in a non-empty list. If it appears more than once, return the first position.",
   '''def index_of_max(nums):
    best = 0
    for i in range(1, len(nums)):
        if nums[i] > nums[best]:
            best = i
    return best''', [([3, 9, 2], 1), ([5, 5], 0)], [[1], [-3, -1, -2], [1, 2, 3, 4], [9, 1, 9], [0, 0, 0, 1]])
fn("below-the-average", "Below the Average", U, "easy", "Counting and searching",
   "Write `below_average(nums)` counting how many numbers are strictly less than the average of the list. An empty list gives 0.",
   '''def below_average(nums):
    if not nums:
        return 0
    average = sum(nums) / len(nums)
    count = 0
    for n in nums:
        if n < average:
            count += 1
    return count''', [([1, 2, 3, 4], 2), ([], 0)], [[5], [1, 1, 1], [1, 100], [10, 20, 30, 40, 50], [-5, 0, 5]])
fn("pairs-with-a-difference", "Pairs With a Difference", U, "medium", "Nested loops",
   "Write `pairs_with_gap(nums, k)` counting pairs of positions i < j where the two numbers differ by exactly k. k is never negative.",
   '''def pairs_with_gap(nums, k):
    count = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if abs(nums[i] - nums[j]) == k:
                count += 1
    return count''', [(([1, 5, 3, 4, 2], 2), 3), (([1, 1, 1], 0), 3)], [([], 1), ([1], 0), ([1, 2, 3], 1), ([10, 20], 10), ([1, 3, 1, 3], 2)])
fn("number-staircase", "Number Staircase", U, "easy", "Nested loops",
   'Write `staircase(n)` returning n rows of text, where row i holds the digits 1 to i joined together. For n = 3 that is `["1", "12", "123"]`. n is at most 9.',
   '''def staircase(n):
    rows = []
    for i in range(1, n + 1):
        row = ""
        for d in range(1, i + 1):
            row += str(d)
        rows.append(row)
    return rows''', [(3, ["1", "12", "123"]), (0, [])], [1, 5, 9, 2, 4])
fn("sum-of-squares", "Sum of Squares", U, "easy", "Running totals", "Write `squares_total(n)` returning 1² + 2² + ... + n², which is 0 when n is 0.",
   "def squares_total(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i * i\n    return total", [(3, 14), (0, 0)], [1, 2, 10, 100, 7])

U = "functions"
fn("perimeter-and-area", "Perimeter and Area", U, "easy", "Parameters and return values", "Write `measure(width, height)` returning `[perimeter, area]` for a rectangle.",
   "def measure(width, height):\n    return [2 * (width + height), width * height]", [((3, 4), [14, 12]), ((1, 1), [4, 1])], [(0, 5), (10, 2), (2.5, 4), (7, 7)])
fn("join-words", "Join Words", U, "easy", "Default and keyword arguments",
   'Write `join_words(words, sep=" ")` joining the words with `sep` between them. When no separator is given, use a space.',
   'def join_words(words, sep=" "):\n    return sep.join(words)', [(["a", "b", "c"], "a b c"), ((["a", "b"], "-"), "a-b")],
   [[], ["x"], (["x", "y"], ""), (["1", "2", "3"], ", "), ["hello", "world"]])
fn("repeat-text", "Repeat Text", U, "easy", "Default and keyword arguments", "Write `repeat(text, times=2)` returning the text repeated `times` times.",
   "def repeat(text, times=2):\n    return text * times", [("ab", "abab"), (("x", 3), "xxx")], ["", ("hi", 0), ("-", 5), "go", ("ab", 1)])
exprs("count-matching-items", "Count Matching Items", U, "easy", "Functions as values",
      "Write `count_if(test, items)` counting the items for which the function `test` returns True.",
      "def count_if(test, items):\n    return sum(1 for item in items if test(item))",
      [("count_if(lambda x: x > 2, [1, 2, 3, 4])", 2), ("count_if(str.isupper, ['A', 'b', 'C'])", 2)],
      ["count_if(bool, [])", "count_if(lambda x: x % 2 == 0, [1, 3, 5])", "count_if(lambda x: True, [1, 2, 3])", "count_if(str.isdigit, ['1', 'a', '22', ''])",
       "count_if(lambda w: len(w) > 3, ['tree', 'a', 'house'])", "count_if(lambda x: x is None, [None, 0, None])", "count_if(lambda x: x < 0, [-1, -2, 3, -4])",
       "count_if(callable, [len, 1, print])", "count_if(lambda s: s.startswith('a'), ['ant', 'bee', 'ape'])", "count_if(lambda n: n == 0, [0, 0, 0, 0])"])
exprs("apply-n-times", "Apply N Times", U, "medium", "Functions as values",
      "Write `apply_n(f, x, n)` that calls `f` on `x`, then on the result, n times in all, and returns the final value. When n is 0, return x unchanged.",
      "def apply_n(f, x, n):\n    for _ in range(n):\n        x = f(x)\n    return x",
      [("apply_n(lambda x: x * 2, 1, 3)", 8), ("apply_n(str.upper, 'hi', 0)", "hi")],
      ["apply_n(lambda x: x + 1, 0, 10)", "apply_n(lambda s: s + 'a', '', 4)", "apply_n(abs, -5, 1)", "apply_n(lambda x: x // 2, 100, 3)",
       "apply_n(lambda xs: xs + [len(xs)], [], 3)", "apply_n(lambda x: -x, 7, 5)", "apply_n(lambda x: x * x, 2, 4)", "apply_n(sorted, [3, 1, 2], 2)",
       "apply_n(lambda s: s[1:], 'abcdef', 2)", "apply_n(lambda x: x - 3, 0, 0)"])
fn("prime-palindromes", "Prime Palindromes", U, "medium", "Breaking problems into helpers",
   "Write `prime_palindromes(limit)` returning, in order, every number up to and including `limit` that is prime and also reads the same backwards. Write a helper for each check, then combine them.",
   '''def is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True

def is_palindrome(n):
    return str(n) == str(n)[::-1]

def prime_palindromes(limit):
    return [n for n in range(2, limit + 1) if is_palindrome(n) and is_prime(n)]''', [(20, [2, 3, 5, 7, 11]), (1, [])], [2, 10, 101, 200, 0, 383])
fn("best-scoring-word", "Best Scoring Word", U, "medium", "Breaking problems into helpers",
   'Each letter scores its place in the alphabet: a is 1, b is 2, and so on up to z at 26. Write `best_word(words)` returning the word with the highest total, the earliest one on a tie, or `""` for an empty list. Words are lowercase and never empty. A helper that scores one word keeps this tidy.',
   '''def score(word):
    return sum(ord(ch) - ord("a") + 1 for ch in word)

def best_word(words):
    best = ""
    for word in words:
        if best == "" or score(word) > score(best):
            best = word
    return best''', [(["abc", "zz", "b"], "zz"), ([], "")], [["a"], ["ab", "ba"], ["hello", "world"], ["cab", "bad", "dab"], ["z", "aaaa"]])

U = "strings"
fn("last-n-characters", "Last N Characters", U, "easy", "Indexing and slicing",
   'Write `last_n(text, n)` returning the last n characters of the text, or all of it when n is larger than its length. When n is 0, return `""`.',
   "def last_n(text, n):\n    return text[max(0, len(text) - n):]", [(("python", 3), "hon"), (("hi", 5), "hi"), (("abc", 0), "")], [("", 2), ("a", 1), ("hello world", 5), ("xyz", 3)])
fn("words-to-snake-case", "Words to Snake Case", U, "easy", "String methods",
   'Write `to_snake(text)` turning words separated by spaces into lowercase words joined by underscores, so `"Hello Big World"` becomes `"hello_big_world"`. Extra spaces are ignored.',
   'def to_snake(text):\n    return "_".join(text.lower().split())', [("Hello Big World", "hello_big_world"), ("  one  ", "one")], ["", "A", "already_snake", "Mixed CASE words here", "x  y"])
fn("count-capital-letters", "Count Capital Letters", U, "easy", "Counting characters", "Write `count_upper(text)` counting the capital letters in the text.",
   "def count_upper(text):\n    return sum(1 for ch in text if ch.isupper())", [("Hello World", 2), ("", 0)], ["ABC", "abc", "PyThOn 3", "123!", "aBc DeF"])
fn("count-different-characters", "Count Different Characters", U, "easy", "Counting characters",
   "Write `different_chars(text)` counting how many different characters the text has. Capital and small letters count as different characters.",
   "def different_chars(text):\n    return len(set(text))", [("hello", 4), ("", 0)], ["aaaa", "abcABC", "banana", "a b c", "112233"])
fn("initials-of-a-name", "Initials of a Name", U, "easy", "Building strings",
   'Write `initials(name)` returning the first letter of each word in capitals, each followed by a dot, so `"ada lovelace"` gives `"A.L."`.',
   'def initials(name):\n    return "".join(word[0].upper() + "." for word in name.split())', [("ada lovelace", "A.L."), ("Grace", "G.")], ["", "a b c", "  linus   torvalds ", "Guido van rossum", "x"])
fn("mirror-a-string", "Mirror a String", U, "easy", "Building strings", 'Write `mirror(text)` returning the text followed by its reverse, so `"ab"` gives `"abba"`.',
   "def mirror(text):\n    return text + text[::-1]", [("ab", "abba"), ("", "")], ["a", "abc", "race", "12"])
fn("rotation-of-another-string", "Rotation of Another String", U, "medium", "Palindromes and comparison",
   'Write `is_rotation(a, b)` returning True when b can be made by moving some letters from the front of a to its end. `"cdab"` is a rotation of `"abcd"`, and every string is a rotation of itself.',
   "def is_rotation(a, b):\n    return len(a) == len(b) and b in a + a", [(("abcd", "cdab"), True), (("abc", "acb"), False)],
   [("", ""), ("a", "a"), ("aa", "a"), ("waterbottle", "erbottlewat"), ("abc", "abc"), ("ab", "ba"), ("abcd", "dabc"), ("aab", "abb")])
fn("almost-a-palindrome", "Almost a Palindrome", U, "medium", "Palindromes and comparison",
   "Write `almost_pal(text)` returning True when the text reads the same backwards, or would after removing one character. Compare from both ends, and where two characters differ, try skipping either one.",
   '''def almost_pal(text):
    def is_pal(i, j):
        while i < j:
            if text[i] != text[j]:
                return False
            i += 1
            j -= 1
        return True
    i, j = 0, len(text) - 1
    while i < j:
        if text[i] != text[j]:
            return is_pal(i + 1, j) or is_pal(i, j - 1)
        i += 1
        j -= 1
    return True''', [("abca", True), ("abc", False), ("racecar", True)], ["", "a", "ab", "abcba", "abccbx", "deeee", "eedede", "cbbcc"])

U = "lists-dicts"
fn("drop-the-negatives", "Drop the Negatives", U, "easy", "Comprehensions", "Write `non_negative(nums)` returning the numbers that are zero or more, in order, using a list comprehension.",
   "def non_negative(nums):\n    return [n for n in nums if n >= 0]", [([3, -1, 0, -5, 2], [3, 0, 2]), ([], [])], [[-1], [1, 2, 3], [-3, -2, -1, 0], [0]])
fn("add-two-lists-together", "Add Two Lists Together", U, "easy", "Comprehensions",
   "Write `pair_sums(a, b)` for two lists of the same length, returning a list where each item is the sum of the two items at that position.",
   "def pair_sums(a, b):\n    return [x + y for x, y in zip(a, b)]", [(([1, 2, 3], [10, 20, 30]), [11, 22, 33]), (([], []), [])], [([5], [-5]), ([1, 1], [2, 2]), ([0, -1, 2], [3, 4, -5])])
fn("matrix-column-sums", "Matrix Column Sums", U, "easy", "Nested lists and matrices",
   "Write `col_sums(matrix)` returning the total of each column, for a non-empty matrix whose rows all have the same length.",
   "def col_sums(matrix):\n    return [sum(row[c] for row in matrix) for c in range(len(matrix[0]))]", [([[1, 2], [3, 4]], [4, 6]), ([[5, 6, 7]], [5, 6, 7])],
   [[[1], [2], [3]], [[0, 0], [0, 0]], [[1, -1, 2], [3, 4, -5], [6, 7, 8]], [[9]]])
fn("identity-matrix", "Identity Matrix", U, "easy", "Nested lists and matrices",
   "Write `identity(n)` returning an n by n matrix with 1 on the diagonal from top left to bottom right, and 0 everywhere else.",
   "def identity(n):\n    return [[1 if r == c else 0 for c in range(n)] for r in range(n)]", [(2, [[1, 0], [0, 1]]), (0, [])], [1, 3, 5, 4])
fn("count-words-by-length", "Count Words by Length", U, "easy", "Grouping and counting",
   "Write `count_by_length(words)` returning a dictionary that maps each word length to how many words have that length.",
   "def count_by_length(words):\n    counts = {}\n    for word in words:\n        counts[len(word)] = counts.get(len(word), 0) + 1\n    return counts",
   [(["a", "bb", "cc", "d"], {1: 2, 2: 2}), ([], {})], [["hello"], ["x", "y", "z"], ["one", "three", "five", "to"]])
fn("dictionary-from-two-lists", "Dictionary From Two Lists", U, "easy", "Dictionary basics",
   "Write `zip_dict(keys, values)` building a dictionary from a list of keys and a list of values of the same length. If a key repeats, the later value wins.",
   "def zip_dict(keys, values):\n    return dict(zip(keys, values))", [((["a", "b"], [1, 2]), {"a": 1, "b": 2}), (([], []), {})], [(["x"], [0]), (["a", "a"], [1, 2]), (["k", "v", "w"], [3, 2, 1])])
fn("keys-with-a-value", "Keys With a Given Value", U, "easy", "Dictionary basics", "Write `keys_for(d, value)` returning, in alphabetical order, every key whose value equals `value`.",
   "def keys_for(d, value):\n    return sorted(k for k, v in d.items() if v == value)", [(({"a": 1, "b": 2, "c": 1}, 1), ["a", "c"]), (({}, 5), [])],
   [({"x": 0}, 1), ({"z": 3, "y": 3}, 3), ({"p": "q"}, "q"), ({"m": 1, "n": 2, "o": 1, "k": 1}, 1)])
fn("running-maximum", "Running Maximum", U, "easy", "List basics", "Write `running_max(nums)` returning a list where each item is the largest number seen so far.",
   '''def running_max(nums):
    out = []
    for n in nums:
        out.append(n if not out else max(out[-1], n))
    return out''', [([1, 3, 2, 5, 4], [1, 3, 3, 5, 5]), ([], [])], [[7], [5, 4, 3], [-1, -2, 0], [2, 2, 2]])
