"""Structured 49-concept Python curriculum across Foundations, Collections, Intermediate Python, and Problem Solving."""
import json

CURRICULUM_CONCEPTS = [
    # --- PILLAR 1: FOUNDATIONS (1-15) ---
    {
        "id": "variables",
        "title": "Variables",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 1,
        "description": "Naming conventions, memory assignment, and dynamic typing in Python.",
        "learning_objectives": "Understand variable declaration, identifier rules, and value reassignment.",
        "explanation": "In Python, variables are labels bound to objects in memory. You do not declare types explicitly. Assignment is performed using '='.",
        "examples": [{"title": "Assigning Variables", "code": "x = 10\nname = 'Alice'\nprint(f'{name} has {x} points')"}],
        "prerequisites": [],
        "problems": [
            {
                "id": 101,
                "title": "Variable Swap",
                "description": "Write swap_values(a, b) returning a tuple (b, a).",
                "difficulty": "easy",
                "topic": "variables",
                "starter_code": "def swap_values(a, b):\n    # Return a tuple with values swapped\n    pass",
                "expected_behavior": "swap_values(1, 2) returns (2, 1)",
                "test_cases": [
                    {"input": [1, 2], "expected": [2, 1]},
                    {"input": ["hello", "world"], "expected": ["world", "hello"]}
                ]
            }
        ]
    },
    {
        "id": "data-types",
        "title": "Data Types",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 2,
        "description": "Core scalar types: int, float, str, bool, and type conversions.",
        "learning_objectives": "Distinguish between numeric and text data types and cast between them.",
        "explanation": "Python features built-in types such as int, float, str, and bool. The type() function inspects an object's type, and constructor functions like int() or str() perform conversion.",
        "examples": [{"title": "Type Casting", "code": "num_str = '42'\nnum_int = int(num_str)\npi_float = float('3.14')"}],
        "prerequisites": ["variables"],
        "problems": [
            {
                "id": 102,
                "title": "Type Converter",
                "description": "Write parse_and_sum(str_a, str_b) taking two numeric strings and returning their integer sum.",
                "difficulty": "easy",
                "topic": "data-types",
                "starter_code": "def parse_and_sum(str_a, str_b):\n    pass",
                "expected_behavior": "parse_and_sum('10', '25') returns 35",
                "test_cases": [
                    {"input": ["10", "25"], "expected": 35},
                    {"input": ["-5", "5"], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "input-output",
        "title": "Input and Output",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 3,
        "description": "Using print(), formatted strings (f-strings), and reading standard input.",
        "learning_objectives": "Format output strings accurately using f-strings and understand string templating.",
        "explanation": "Output is printed using print(). F-strings (f'...') provide concise, readable interpolation of expressions directly within string literals.",
        "examples": [{"title": "Formatted String", "code": "score = 95\nprint(f'Final Score: {score:.1f}%')"}],
        "prerequisites": ["variables", "data-types"],
        "problems": [
            {
                "id": 103,
                "title": "Format Greeting",
                "description": "Write format_greeting(name, age) returning 'Hello <name>, you are <age> years old!'.",
                "difficulty": "easy",
                "topic": "input-output",
                "starter_code": "def format_greeting(name, age):\n    pass",
                "expected_behavior": "format_greeting('Ada', 36) returns 'Hello Ada, you are 36 years old!'",
                "test_cases": [
                    {"input": ["Ada", 36], "expected": "Hello Ada, you are 36 years old!"},
                    {"input": ["Bob", 20], "expected": "Hello Bob, you are 20 years old!"}
                ]
            }
        ]
    },
    {
        "id": "operators",
        "title": "Operators",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 4,
        "description": "Arithmetic, comparison, logical, and membership operators.",
        "learning_objectives": "Apply operator precedence and boolean logic effectively.",
        "explanation": "Arithmetic includes +, -, *, /, // (floor div), % (modulo), and ** (power). Comparison includes ==, !=, <, <=, >, >=. Logical operators are and, or, not.",
        "examples": [{"title": "Modulo and Division", "code": "even = (10 % 2 == 0)\nfloor = 7 // 2  # 3"}],
        "prerequisites": ["variables", "data-types"],
        "problems": [
            {
                "id": 104,
                "title": "Even or Odd Checker",
                "description": "Write is_even(n) returning True if n is even, False otherwise.",
                "difficulty": "easy",
                "topic": "operators",
                "starter_code": "def is_even(n):\n    pass",
                "expected_behavior": "is_even(4) returns True; is_even(7) returns False",
                "test_cases": [
                    {"input": [4], "expected": True},
                    {"input": [7], "expected": False},
                    {"input": [0], "expected": True}
                ]
            }
        ]
    },
    {
        "id": "if-statements",
        "title": "If Statements",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 5,
        "description": "Single-branch conditional execution using boolean guards.",
        "learning_objectives": "Execute code blocks conditionally when a predicate evaluates to True.",
        "explanation": "The 'if' statement evaluates a conditional expression. If the expression evaluates to True, the indented block of code runs.",
        "examples": [{"title": "Basic If", "code": "if score >= 60:\n    status = 'Passed'"}],
        "prerequisites": ["operators"],
        "problems": [
            {
                "id": 105,
                "title": "Absolute Value",
                "description": "Write get_abs(n) that returns the absolute value of n using an if statement.",
                "difficulty": "easy",
                "topic": "if-statements",
                "starter_code": "def get_abs(n):\n    pass",
                "expected_behavior": "get_abs(-9) returns 9; get_abs(5) returns 5",
                "test_cases": [
                    {"input": [-9], "expected": 9},
                    {"input": [5], "expected": 5},
                    {"input": [0], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "if-else",
        "title": "If / Else",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 6,
        "description": "Two-branch decision making.",
        "learning_objectives": "Handle mutually exclusive logic paths.",
        "explanation": "An 'if...else' construct executes one block when the condition is True, and the alternative block when it is False.",
        "examples": [{"title": "If Else", "code": "if age >= 18:\n    access = 'Adult'\nelse:\n    access = 'Minor'"}],
        "prerequisites": ["if-statements"],
        "problems": [
            {
                "id": 106,
                "title": "Sign of Number",
                "description": "Write sign_description(n) returning 'positive' if n > 0 else 'non-positive'.",
                "difficulty": "easy",
                "topic": "if-else",
                "starter_code": "def sign_description(n):\n    pass",
                "expected_behavior": "sign_description(5) returns 'positive'; sign_description(-2) returns 'non-positive'",
                "test_cases": [
                    {"input": [5], "expected": "positive"},
                    {"input": [-2], "expected": "non-positive"},
                    {"input": [0], "expected": "non-positive"}
                ]
            }
        ]
    },
    {
        "id": "if-elif-else",
        "title": "If / Elif / Else",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 7,
        "description": "Multi-way conditional branching.",
        "learning_objectives": "Evaluate sequential conditions with a default fallback.",
        "explanation": "The 'elif' clause allows testing multiple expressions in sequence until one evaluates to True. The optional 'else' clause catches any remaining cases.",
        "examples": [{"title": "Letter Grade", "code": "if score >= 90:\n    grade = 'A'\nelif score >= 80:\n    grade = 'B'\nelse:\n    grade = 'C'"}],
        "prerequisites": ["if-else"],
        "problems": [
            {
                "id": 107,
                "title": "Compare Numbers",
                "description": "Write compare(a, b) returning 'greater' if a > b, 'less' if a < b, or 'equal' if a == b.",
                "difficulty": "easy",
                "topic": "if-elif-else",
                "starter_code": "def compare(a, b):\n    pass",
                "expected_behavior": "compare(5, 3) returns 'greater'; compare(2, 4) returns 'less'; compare(3, 3) returns 'equal'",
                "test_cases": [
                    {"input": [5, 3], "expected": "greater"},
                    {"input": [2, 4], "expected": "less"},
                    {"input": [3, 3], "expected": "equal"}
                ]
            }
        ]
    },
    {
        "id": "nested-conditions",
        "title": "Nested Conditions",
        "category": "Foundations",
        "difficulty": "medium",
        "order_index": 8,
        "description": "Hierarchical decision trees using nested if statements.",
        "learning_objectives": "Manage multi-tiered logical constraints with clean indentation.",
        "explanation": "Conditions placed inside other conditional blocks allow nuanced evaluation of dependent criteria.",
        "examples": [{"title": "Nested Check", "code": "if user_active:\n    if user_role == 'admin':\n        grant_full_access()"}],
        "prerequisites": ["if-elif-else"],
        "problems": [
            {
                "id": 108,
                "title": "Leap Year Checker",
                "description": "Write is_leap_year(year) returning True if year is divisible by 4, except century years must be divisible by 400.",
                "difficulty": "medium",
                "topic": "nested-conditions",
                "starter_code": "def is_leap_year(year):\n    pass",
                "expected_behavior": "is_leap_year(2000) -> True, is_leap_year(1900) -> False, is_leap_year(2024) -> True",
                "test_cases": [
                    {"input": [2000], "expected": True},
                    {"input": [1900], "expected": False},
                    {"input": [2024], "expected": True},
                    {"input": [2023], "expected": False}
                ]
            }
        ]
    },
    {
        "id": "for-loops",
        "title": "For Loops",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 9,
        "description": "Definite iteration over ranges and iterable collections.",
        "learning_objectives": "Use range() and iterate over sequences efficiently.",
        "explanation": "A for loop iterates over each item in an iterable sequence (such as a list, string, or range) in order.",
        "examples": [{"title": "Sum with Range", "code": "total = 0\nfor i in range(1, 6):\n    total += i"}],
        "prerequisites": ["operators"],
        "problems": [
            {
                "id": 109,
                "title": "Count Multiples",
                "description": "Write count_multiples(n, limit) returning the count of numbers <= limit that are divisible by n (n > 0).",
                "difficulty": "easy",
                "topic": "for-loops",
                "starter_code": "def count_multiples(n, limit):\n    pass",
                "expected_behavior": "count_multiples(3, 10) returns 3 (3, 6, 9)",
                "test_cases": [
                    {"input": [3, 10], "expected": 3},
                    {"input": [5, 25], "expected": 5},
                    {"input": [10, 5], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "while-loops",
        "title": "While Loops",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 10,
        "description": "Indefinite iteration controlled by a continuing condition.",
        "learning_objectives": "Implement iteration that repeats until a state condition is met.",
        "explanation": "A while loop repeats its body as long as its condition remains True. State must be updated within the loop to avoid infinite loops.",
        "examples": [{"title": "Countdown", "code": "count = 5\nwhile count > 0:\n    count -= 1"}],
        "prerequisites": ["if-statements"],
        "problems": [
            {
                "id": 110,
                "title": "Collatz Steps",
                "description": "Write collatz_steps(n) returning the number of steps to reach 1: if even n//=2, if odd n=3*n+1.",
                "difficulty": "medium",
                "topic": "while-loops",
                "starter_code": "def collatz_steps(n):\n    pass",
                "expected_behavior": "collatz_steps(6) returns 8",
                "test_cases": [
                    {"input": [6], "expected": 8},
                    {"input": [1], "expected": 0},
                    {"input": [2], "expected": 1}
                ]
            }
        ]
    },
    {
        "id": "break",
        "title": "Break",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 11,
        "description": "Premature loop termination.",
        "learning_objectives": "Exit loops immediately when an early stopping criterion is satisfied.",
        "explanation": "The 'break' statement terminates the innermost loop immediately, jumping execution to the first statement outside the loop.",
        "examples": [{"title": "Early Exit", "code": "for x in [1, 3, -1, 5]:\n    if x < 0:\n        break"}],
        "prerequisites": ["for-loops", "while-loops"],
        "problems": [
            {
                "id": 111,
                "title": "First Negative",
                "description": "Write first_negative(numbers) returning the first negative number found in the list, or None if none exist.",
                "difficulty": "easy",
                "topic": "break",
                "starter_code": "def first_negative(numbers):\n    pass",
                "expected_behavior": "first_negative([2, 5, -3, 8]) returns -3",
                "test_cases": [
                    {"input": [[2, 5, -3, 8]], "expected": -3},
                    {"input": [[1, 2, 3]], "expected": None},
                    {"input": [[-5, 2]], "expected": -5}
                ]
            }
        ]
    },
    {
        "id": "continue",
        "title": "Continue",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 12,
        "description": "Skipping to the next loop iteration.",
        "learning_objectives": "Bypass the remainder of a loop body for specific elements.",
        "explanation": "The 'continue' statement stops execution of the current iteration and jumps directly to the next iteration of the loop.",
        "examples": [{"title": "Skip Evens", "code": "for i in range(10):\n    if i % 2 == 0:\n        continue\n    print(i)"}],
        "prerequisites": ["break"],
        "problems": [
            {
                "id": 112,
                "title": "Sum Odds Only",
                "description": "Write sum_odds(numbers) that uses continue to skip even numbers and returns the sum of odds.",
                "difficulty": "easy",
                "topic": "continue",
                "starter_code": "def sum_odds(numbers):\n    pass",
                "expected_behavior": "sum_odds([1, 2, 3, 4, 5]) returns 9",
                "test_cases": [
                    {"input": [[1, 2, 3, 4, 5]], "expected": 9},
                    {"input": [[2, 4, 6]], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "functions",
        "title": "Functions",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 13,
        "description": "Modular, reusable code blocks defined with 'def'.",
        "learning_objectives": "Organize code into callable abstractions.",
        "explanation": "Functions group reusable logic under a name. They are defined using the 'def' keyword and invoked with parentheses.",
        "examples": [{"title": "Simple Function", "code": "def greet():\n    return 'Hello, Python!'"}],
        "prerequisites": ["variables"],
        "problems": [
            {
                "id": 113,
                "title": "Multiply By Two",
                "description": "Write double(n) returning 2 * n.",
                "difficulty": "easy",
                "topic": "functions",
                "starter_code": "def double(n):\n    pass",
                "expected_behavior": "double(7) returns 14",
                "test_cases": [
                    {"input": [7], "expected": 14},
                    {"input": [0], "expected": 0},
                    {"input": [-3], "expected": -6}
                ]
            }
        ]
    },
    {
        "id": "parameters",
        "title": "Parameters",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 14,
        "description": "Positional, keyword, default, and variable arguments (*args, **kwargs).",
        "learning_objectives": "Design flexible function signatures.",
        "explanation": "Parameters define values expected by a function. Default arguments assign fallback values when an argument is omitted during invocation.",
        "examples": [{"title": "Default Parameter", "code": "def power(base, exp=2):\n    return base ** exp"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 114,
                "title": "Power with Default",
                "description": "Write compute_power(base, exp=2) returning base raised to exp.",
                "difficulty": "easy",
                "topic": "parameters",
                "starter_code": "def compute_power(base, exp=2):\n    pass",
                "expected_behavior": "compute_power(3) returns 9; compute_power(2, 3) returns 8",
                "test_cases": [
                    {"input": [3], "expected": 9},
                    {"input": [2, 3], "expected": 8},
                    {"input": [5, 0], "expected": 1}
                ]
            }
        ]
    },
    {
        "id": "return-values",
        "title": "Return Values",
        "category": "Foundations",
        "difficulty": "easy",
        "order_index": 15,
        "description": "Returning results, multiple return values as tuples, and early return patterns.",
        "learning_objectives": "Send computed results back to the caller cleanly.",
        "explanation": "The 'return' statement exits a function and hands the specified value back to the caller. Omitting return implicitly returns None.",
        "examples": [{"title": "Multiple Returns", "code": "def min_max(lst):\n    return min(lst), max(lst)"}],
        "prerequisites": ["parameters"],
        "problems": [
            {
                "id": 115,
                "title": "Min and Max Tuple",
                "description": "Write find_extrema(numbers) returning a tuple (min_val, max_val).",
                "difficulty": "easy",
                "topic": "return-values",
                "starter_code": "def find_extrema(numbers):\n    pass",
                "expected_behavior": "find_extrema([4, 1, 9, 2]) returns (1, 9)",
                "test_cases": [
                    {"input": [[4, 1, 9, 2]], "expected": [1, 9]},
                    {"input": [[5]], "expected": [5, 5]}
                ]
            }
        ]
    },

    # --- PILLAR 2: COLLECTIONS (16-26) ---
    {
        "id": "strings",
        "title": "Strings",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 16,
        "description": "Immutable sequences of Unicode characters, indexing, and iteration.",
        "learning_objectives": "Access characters via 0-based and negative indexing.",
        "explanation": "Strings in Python are immutable text sequences. Character elements can be indexed using bracket syntax, e.g., text[0] or text[-1].",
        "examples": [{"title": "String Indexing", "code": "word = 'Python'\nfirst = word[0]  # 'P'\nlast = word[-1]   # 'n'"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 116,
                "title": "First and Last Char",
                "description": "Write first_and_last(s) returning a 2-character string of the first and last characters of non-empty s.",
                "difficulty": "easy",
                "topic": "strings",
                "starter_code": "def first_and_last(s):\n    pass",
                "expected_behavior": "first_and_last('Tutor') returns 'Tr'",
                "test_cases": [
                    {"input": ["Tutor"], "expected": "Tr"},
                    {"input": ["A"], "expected": "AA"}
                ]
            }
        ]
    },
    {
        "id": "string-methods",
        "title": "String Methods",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 17,
        "description": "Built-in transformations: split, join, lower, upper, strip, replace.",
        "learning_objectives": "Manipulate and sanitize text using standard string methods.",
        "explanation": "Strings provide helper methods such as .lower(), .upper(), .strip(), .replace(), and .split(). Since strings are immutable, methods return a new string.",
        "examples": [{"title": "Split and Join", "code": "words = 'apple,banana,orange'.split(',')\nclean = ' - '.join(words)"}],
        "prerequisites": ["strings"],
        "problems": [
            {
                "id": 117,
                "title": "Clean and Capitalize",
                "description": "Write clean_words(sentence) that strips leading/trailing spaces, splits by spaces, and returns list of uppercase words.",
                "difficulty": "easy",
                "topic": "string-methods",
                "starter_code": "def clean_words(sentence):\n    pass",
                "expected_behavior": "clean_words('  hello world  ') returns ['HELLO', 'WORLD']",
                "test_cases": [
                    {"input": ["  hello world  "], "expected": ["HELLO", "WORLD"]},
                    {"input": ["python"], "expected": ["PYTHON"]}
                ]
            }
        ]
    },
    {
        "id": "lists",
        "title": "Lists",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 18,
        "description": "Ordered, mutable sequences that store heterogeneous items.",
        "learning_objectives": "Construct, read, and mutate list collections.",
        "explanation": "Lists are mutable sequences defined using brackets: [item1, item2]. Elements can be modified in place: items[0] = new_value.",
        "examples": [{"title": "List Mutation", "code": "nums = [1, 2, 3]\nnums[0] = 10\nprint(nums)  # [10, 2, 3]"}],
        "prerequisites": ["return-values"],
        "problems": [
            {
                "id": 118,
                "title": "Sum Positive Numbers",
                "description": "Write sum_positives(numbers) returning the sum of all positive numbers in a list.",
                "difficulty": "easy",
                "topic": "lists",
                "starter_code": "def sum_positives(numbers):\n    pass",
                "expected_behavior": "sum_positives([1, -4, 7, 12]) returns 20",
                "test_cases": [
                    {"input": [[1, -4, 7, 12]], "expected": 20},
                    {"input": [[-1, -2, -3]], "expected": 0},
                    {"input": [[]], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "list-methods",
        "title": "List Methods",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 19,
        "description": "In-place modifications: append, extend, insert, pop, remove, sort.",
        "learning_objectives": "Mutate lists using in-place methods vs returning new lists.",
        "explanation": ".append(x) adds an item to the end, .pop() removes and returns an item, and .sort() orders the list in place.",
        "examples": [{"title": "List Mutation Methods", "code": "stack = []\nstack.append(1)\nval = stack.pop()"}],
        "prerequisites": ["lists"],
        "problems": [
            {
                "id": 119,
                "title": "Sort and Deduplicate",
                "description": "Write sort_and_remove_duplicates(numbers) returning a new sorted list without duplicate values.",
                "difficulty": "easy",
                "topic": "list-methods",
                "starter_code": "def sort_and_remove_duplicates(numbers):\n    pass",
                "expected_behavior": "sort_and_remove_duplicates([4, 2, 4, 1, 2]) returns [1, 2, 4]",
                "test_cases": [
                    {"input": [[4, 2, 4, 1, 2]], "expected": [1, 2, 4]},
                    {"input": [[3, 3, 3]], "expected": [3]}
                ]
            }
        ]
    },
    {
        "id": "tuples",
        "title": "Tuples",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 20,
        "description": "Immutable ordered sequences, packing, and unpacking.",
        "learning_objectives": "Utilize tuples for fixed-structure data records and unpacking.",
        "explanation": "Tuples are immutable sequences created using parentheses: (a, b). They are hashable (can be dict keys) and prevent accidental modification.",
        "examples": [{"title": "Tuple Unpacking", "code": "point = (10, 20)\nx, y = point"}],
        "prerequisites": ["lists"],
        "problems": [
            {
                "id": 120,
                "title": "Euclidean Distance Squared",
                "description": "Write dist_sq(p1, p2) taking two 2D coordinate tuples and returning (x2 - x1)**2 + (y2 - y1)**2.",
                "difficulty": "easy",
                "topic": "tuples",
                "starter_code": "def dist_sq(p1, p2):\n    pass",
                "expected_behavior": "dist_sq((0, 0), (3, 4)) returns 25",
                "test_cases": [
                    {"input": [[0, 0], [3, 4]], "expected": 25},
                    {"input": [[1, 1], [4, 5]], "expected": 25}
                ]
            }
        ]
    },
    {
        "id": "sets",
        "title": "Sets",
        "category": "Collections",
        "difficulty": "medium",
        "order_index": 21,
        "description": "Unordered collections of unique elements with set algebra operations.",
        "learning_objectives": "Execute set operations (union, intersection, difference) for O(1) membership.",
        "explanation": "Sets store distinct hashable elements. They provide mathematical operations such as union (|), intersection (&), and difference (-).",
        "examples": [{"title": "Set Intersection", "code": "a = {1, 2, 3}\nb = {2, 3, 4}\ncommon = a & b  # {2, 3}"}],
        "prerequisites": ["tuples"],
        "problems": [
            {
                "id": 121,
                "title": "Shared Elements",
                "description": "Write common_elements(list1, list2) returning a sorted list of unique elements present in both lists.",
                "difficulty": "medium",
                "topic": "sets",
                "starter_code": "def common_elements(list1, list2):\n    pass",
                "expected_behavior": "common_elements([1, 2, 3], [2, 3, 4]) returns [2, 3]",
                "test_cases": [
                    {"input": [[1, 2, 3], [2, 3, 4]], "expected": [2, 3]},
                    {"input": [[1, 2], [3, 4]], "expected": []}
                ]
            }
        ]
    },
    {
        "id": "dictionaries",
        "title": "Dictionaries",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 22,
        "description": "Key-value hash maps, key lookups, and dynamic updates.",
        "learning_objectives": "Map unique keys to values and access values in O(1) average time.",
        "explanation": "Dictionaries store key-value associations: {key: value}. Keys must be immutable and hashable; values can be any object.",
        "examples": [{"title": "Dictionary Lookup", "code": "ages = {'Ada': 36, 'Alan': 41}\nprint(ages['Ada'])"}],
        "prerequisites": ["lists"],
        "problems": [
            {
                "id": 122,
                "title": "Count Frequencies",
                "description": "Write count_frequencies(items) returning a dictionary mapping each distinct element to its occurrence count.",
                "difficulty": "easy",
                "topic": "dictionaries",
                "starter_code": "def count_frequencies(items):\n    pass",
                "expected_behavior": "count_frequencies(['a', 'b', 'a']) returns {'a': 2, 'b': 1}",
                "test_cases": [
                    {"input": [["a", "b", "a"]], "expected": {"a": 2, "b": 1}},
                    {"input": [[]], "expected": {}}
                ]
            }
        ]
    },
    {
        "id": "dictionary-methods",
        "title": "Dictionary Methods",
        "category": "Collections",
        "difficulty": "medium",
        "order_index": 23,
        "description": ".get(), .keys(), .values(), .items(), .update(), and .setdefault().",
        "learning_objectives": "Use safe key retrieval with defaults and iterate over key-value pairs.",
        "explanation": "dict.get(key, default) avoids KeyError when a key may be absent. .items() yields (key, value) pairs during iteration.",
        "examples": [{"title": "Safe Get", "code": "user = {'name': 'Sam'}\nrole = user.get('role', 'guest')"}],
        "prerequisites": ["dictionaries"],
        "problems": [
            {
                "id": 123,
                "title": "Invert Dictionary",
                "description": "Write invert_dict(d) that swaps keys and values (assuming values are unique).",
                "difficulty": "medium",
                "topic": "dictionary-methods",
                "starter_code": "def invert_dict(d):\n    pass",
                "expected_behavior": "invert_dict({'a': 1, 'b': 2}) returns {1: 'a', 2: 'b'}",
                "test_cases": [
                    {"input": [{"a": 1, "b": 2}], "expected": {1: "a", 2: "b"}},
                    {"input": [{}], "expected": {}}
                ]
            }
        ]
    },
    {
        "id": "slicing",
        "title": "Slicing",
        "category": "Collections",
        "difficulty": "easy",
        "order_index": 24,
        "description": "Extracting sub-sequences using [start:stop:step] slice notation.",
        "learning_objectives": "Extract sub-lists and reverse sequences with step values.",
        "explanation": "Sequence slicing syntax [start:stop:step] extracts a portion of a sequence. Negative steps iterate backwards (e.g. [::-1] reverses).",
        "examples": [{"title": "Reverse Slice", "code": "text = 'hello'\nrev = text[::-1]  # 'olleh'"}],
        "prerequisites": ["strings", "lists"],
        "problems": [
            {
                "id": 124,
                "title": "Every Second Element",
                "description": "Write every_second(lst) returning every second element starting at index 0.",
                "difficulty": "easy",
                "topic": "slicing",
                "starter_code": "def every_second(lst):\n    pass",
                "expected_behavior": "every_second([10, 20, 30, 40, 50]) returns [10, 30, 50]",
                "test_cases": [
                    {"input": [[10, 20, 30, 40, 50]], "expected": [10, 30, 50]},
                    {"input": [[1]], "expected": [1]}
                ]
            }
        ]
    },
    {
        "id": "list-comprehensions",
        "title": "List Comprehensions",
        "category": "Collections",
        "difficulty": "medium",
        "order_index": 25,
        "description": "Concise declarative syntax for filtering and transforming lists.",
        "learning_objectives": "Write readable, idiomatic one-line list transformations.",
        "explanation": "List comprehensions follow the form: [expression for item in iterable if condition]. They are faster and more concise than manual append loops.",
        "examples": [{"title": "Squares of Evens", "code": "evens = [x**2 for x in range(10) if x % 2 == 0]"}],
        "prerequisites": ["lists", "for-loops"],
        "problems": [
            {
                "id": 125,
                "title": "Square Positives Comprehension",
                "description": "Write square_positives(numbers) returning a list of squares of only positive numbers.",
                "difficulty": "medium",
                "topic": "list-comprehensions",
                "starter_code": "def square_positives(numbers):\n    pass",
                "expected_behavior": "square_positives([-2, 1, 3, -4]) returns [1, 9]",
                "test_cases": [
                    {"input": [[-2, 1, 3, -4]], "expected": [1, 9]},
                    {"input": [[-5, -1]], "expected": []}
                ]
            }
        ]
    },
    {
        "id": "dictionary-comprehensions",
        "title": "Dictionary Comprehensions",
        "category": "Collections",
        "difficulty": "medium",
        "order_index": 26,
        "description": "Constructing dictionaries concisely using {k: v for ... in ...}.",
        "learning_objectives": "Transform key-value mappings declaratively.",
        "explanation": "Dict comprehensions allow constructing dictionaries in one expression: {key_expr: val_expr for item in iterable if condition}.",
        "examples": [{"title": "Word Lengths", "code": "words = ['cat', 'elephant']\nlengths = {w: len(w) for w in words}"}],
        "prerequisites": ["dictionaries", "list-comprehensions"],
        "problems": [
            {
                "id": 126,
                "title": "Character Count Map",
                "description": "Write word_lengths(words) returning a dict mapping each word to its character length.",
                "difficulty": "medium",
                "topic": "dictionary-comprehensions",
                "starter_code": "def word_lengths(words):\n    pass",
                "expected_behavior": "word_lengths(['hi', 'tutor']) returns {'hi': 2, 'tutor': 5}",
                "test_cases": [
                    {"input": [["hi", "tutor"]], "expected": {"hi": 2, "tutor": 5}},
                    {"input": [[]], "expected": {}}
                ]
            }
        ]
    },

    # --- PILLAR 3: INTERMEDIATE PYTHON (27-41) ---
    {
        "id": "scope",
        "title": "Scope",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 27,
        "description": "LEGB rule (Local, Enclosing, Global, Built-in), and global/nonlocal keywords.",
        "learning_objectives": "Understand variable resolution order and lexical closures.",
        "explanation": "Python resolves variables via LEGB: Local first, then Enclosing (closure), Global (module level), and Built-in.",
        "examples": [{"title": "Closure Counter", "code": "def make_adder(x):\n    def add(y):\n        return x + y\n    return add"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 127,
                "title": "Multiplier Factory",
                "description": "Write make_multiplier(factor) returning a function that multiplies its argument by factor.",
                "difficulty": "medium",
                "topic": "scope",
                "starter_code": "def make_multiplier(factor):\n    pass",
                "expected_behavior": "fn = make_multiplier(3); fn(5) returns 15",
                "test_cases": [
                    {"input": [3], "expected_type": "closure", "eval_with": 5, "expected": 15}
                ]
            }
        ]
    },
    {
        "id": "recursion",
        "title": "Recursion",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 28,
        "description": "Functions calling themselves with base case and recursive step.",
        "learning_objectives": "Formulate divide-and-conquer logic with sound base cases.",
        "explanation": "A recursive function calls itself to solve smaller sub-problems. Every recursive function must define a base case to terminate execution.",
        "examples": [{"title": "Factorial", "code": "def fact(n):\n    return 1 if n <= 1 else n * fact(n - 1)"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 128,
                "title": "Recursive Factorial",
                "description": "Write factorial(n) returning n! for non-negative integer n.",
                "difficulty": "medium",
                "topic": "recursion",
                "starter_code": "def factorial(n):\n    pass",
                "expected_behavior": "factorial(5) returns 120",
                "test_cases": [
                    {"input": [5], "expected": 120},
                    {"input": [0], "expected": 1},
                    {"input": [1], "expected": 1}
                ]
            }
        ]
    },
    {
        "id": "lambda-functions",
        "title": "Lambda Functions",
        "category": "Intermediate Python",
        "difficulty": "easy",
        "order_index": 29,
        "description": "Anonymous single-expression functions defined inline.",
        "learning_objectives": "Write concise inline callables for sorting and transformations.",
        "explanation": "Lambda expressions provide a syntax for anonymous functions: lambda args: expression. They are restricted to a single evaluated expression.",
        "examples": [{"title": "Sort by Key", "code": "pairs = [(1, 'b'), (2, 'a')]\npairs.sort(key=lambda item: item[1])"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 129,
                "title": "Sort Tuples by Second Item",
                "description": "Write sort_by_second(pairs) returning pairs sorted by their second element using a lambda.",
                "difficulty": "easy",
                "topic": "lambda-functions",
                "starter_code": "def sort_by_second(pairs):\n    pass",
                "expected_behavior": "sort_by_second([(1, 3), (4, 1)]) returns [(4, 1), (1, 3)]",
                "test_cases": [
                    {"input": [[(1, 3), (4, 1)]], "expected": [[4, 1], [1, 3]]}
                ]
            }
        ]
    },
    {
        "id": "map",
        "title": "map()",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 30,
        "description": "Applying a function to every element of an iterable lazily.",
        "learning_objectives": "Utilize functional programming mappings across collections.",
        "explanation": "map(function, iterable) yields items resulting from applying the function to each element of the iterable.",
        "examples": [{"title": "Map to Lengths", "code": "lengths = list(map(len, ['ant', 'bear']))"}],
        "prerequisites": ["lambda-functions"],
        "problems": [
            {
                "id": 130,
                "title": "Map String to Ints",
                "description": "Write parse_integers(strings) using map() to convert a list of numeric strings into integers.",
                "difficulty": "medium",
                "topic": "map",
                "starter_code": "def parse_integers(strings):\n    pass",
                "expected_behavior": "parse_integers(['1', '2', '3']) returns [1, 2, 3]",
                "test_cases": [
                    {"input": [["1", "2", "3"]], "expected": [1, 2, 3]}
                ]
            }
        ]
    },
    {
        "id": "filter",
        "title": "filter()",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 31,
        "description": "Filtering items from an iterable according to a predicate function.",
        "learning_objectives": "Extract subsets of collections lazily using predicate functions.",
        "explanation": "filter(predicate, iterable) extracts elements for which the predicate returns True.",
        "examples": [{"title": "Filter Positives", "code": "pos = list(filter(lambda x: x > 0, [-1, 2, -3, 4]))"}],
        "prerequisites": ["map"],
        "problems": [
            {
                "id": 131,
                "title": "Filter Evens",
                "description": "Write filter_evens(numbers) using filter() to return a list of even integers.",
                "difficulty": "medium",
                "topic": "filter",
                "starter_code": "def filter_evens(numbers):\n    pass",
                "expected_behavior": "filter_evens([1, 2, 3, 4]) returns [2, 4]",
                "test_cases": [
                    {"input": [[1, 2, 3, 4]], "expected": [2, 4]}
                ]
            }
        ]
    },
    {
        "id": "exceptions",
        "title": "Exceptions",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 32,
        "description": "Defensive error handling with try, except, else, and finally.",
        "learning_objectives": "Catch specific runtime errors and maintain program stability.",
        "explanation": "Exceptions signal runtime errors. A try-except block allows intercepting expected errors (e.g. ValueError, ZeroDivisionError) gracefully.",
        "examples": [{"title": "Safe Division", "code": "try:\n    res = a / b\nexcept ZeroDivisionError:\n    res = 0"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 132,
                "title": "Safe Divide",
                "description": "Write safe_divide(a, b) returning a / b, or None if ZeroDivisionError occurs.",
                "difficulty": "medium",
                "topic": "exceptions",
                "starter_code": "def safe_divide(a, b):\n    pass",
                "expected_behavior": "safe_divide(10, 2) returns 5.0; safe_divide(10, 0) returns None",
                "test_cases": [
                    {"input": [10, 2], "expected": 5.0},
                    {"input": [10, 0], "expected": None}
                ]
            }
        ]
    },
    {
        "id": "file-handling",
        "title": "File Handling",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 33,
        "description": "Reading and writing files safely with context managers ('with open(...)').",
        "learning_objectives": "Manage I/O streams and guarantee resource disposal via context managers.",
        "explanation": "The 'with open(path, mode)' statement manages file streams and automatically closes them when the block exits, even if exceptions occur.",
        "examples": [{"title": "Read Lines", "code": "with open('data.txt', 'r') as f:\n    lines = f.readlines()"}],
        "prerequisites": ["exceptions"],
        "problems": [
            {
                "id": 133,
                "title": "Count Lines from Text",
                "description": "Write count_non_empty_lines(text) returning the count of lines in text that contain non-whitespace characters.",
                "difficulty": "medium",
                "topic": "file-handling",
                "starter_code": "def count_non_empty_lines(text):\n    pass",
                "expected_behavior": "count_non_empty_lines('hello\\n\\nworld') returns 2",
                "test_cases": [
                    {"input": ["hello\n\nworld"], "expected": 2},
                    {"input": ["\n   \n"], "expected": 0}
                ]
            }
        ]
    },
    {
        "id": "modules",
        "title": "Modules",
        "category": "Intermediate Python",
        "difficulty": "easy",
        "order_index": 34,
        "description": "Organizing code into files and importing standard libraries (math, random, sys).",
        "learning_objectives": "Import and reuse modular functions from the Python Standard Library.",
        "explanation": "A module is a Python file containing executable code and definitions. Modules are loaded with 'import module_name'.",
        "examples": [{"title": "Math Import", "code": "import math\nroot = math.sqrt(25)  # 5.0"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 134,
                "title": "Circle Area",
                "description": "Write circle_area(radius) returning math.pi * radius**2 rounded to 2 decimal places.",
                "difficulty": "easy",
                "topic": "modules",
                "starter_code": "def circle_area(radius):\n    pass",
                "expected_behavior": "circle_area(3) returns 28.27",
                "test_cases": [
                    {"input": [3], "expected": 28.27},
                    {"input": [0], "expected": 0.0}
                ]
            }
        ]
    },
    {
        "id": "packages",
        "title": "Packages",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 35,
        "description": "Hierarchical module namespaces using directories and __init__.py.",
        "learning_objectives": "Structure multi-file Python applications into packages.",
        "explanation": "Packages are directory structures that group related modules, providing dotted module names.",
        "examples": [{"title": "Package Structure", "code": "# from package.submodule import helper"}],
        "prerequisites": ["modules"],
        "problems": [
            {
                "id": 135,
                "title": "Normalize Module Name",
                "description": "Write package_path_to_module(path) turning 'app/services/tutor.py' into 'app.services.tutor'.",
                "difficulty": "medium",
                "topic": "packages",
                "starter_code": "def package_path_to_module(path):\n    pass",
                "expected_behavior": "package_path_to_module('app/services/tutor.py') returns 'app.services.tutor'",
                "test_cases": [
                    {"input": ["app/services/tutor.py"], "expected": "app.services.tutor"}
                ]
            }
        ]
    },
    {
        "id": "classes",
        "title": "Classes",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 36,
        "description": "User-defined types bundling state (attributes) and behavior (methods).",
        "learning_objectives": "Model real-world entities using object-oriented abstractions.",
        "explanation": "Classes serve as blueprints for objects. Methods defined inside a class accept 'self' as their first argument referring to the instance.",
        "examples": [{"title": "Simple Class", "code": "class Dog:\n    def speak(self):\n        return 'Woof!'"}],
        "prerequisites": ["functions"],
        "problems": [
            {
                "id": 136,
                "title": "Counter Class",
                "description": "Write class Counter with increment() and get_count() methods, starting at 0.",
                "difficulty": "medium",
                "topic": "classes",
                "starter_code": "class Counter:\n    def __init__(self):\n        self.count = 0\n    def increment(self):\n        pass\n    def get_count(self):\n        pass",
                "expected_behavior": "c = Counter(); c.increment(); c.get_count() returns 1",
                "test_cases": [
                    {"test_script": "c = Counter()\nc.increment()\nc.increment()\nassert c.get_count() == 2"}
                ]
            }
        ]
    },
    {
        "id": "objects",
        "title": "Objects",
        "category": "Intermediate Python",
        "difficulty": "easy",
        "order_index": 37,
        "description": "Instantiating and interacting with class instances.",
        "learning_objectives": "Manipulate instance state and call instance methods.",
        "explanation": "An object is a concrete instance of a class, possessing its own unique attribute values.",
        "examples": [{"title": "Instantiating", "code": "c1 = Counter()\nc2 = Counter()"}],
        "prerequisites": ["classes"],
        "problems": [
            {
                "id": 137,
                "title": "Point Class",
                "description": "Write class Point(x, y) with a method move(dx, dy) that updates self.x and self.y.",
                "difficulty": "easy",
                "topic": "objects",
                "starter_code": "class Point:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y\n    def move(self, dx, dy):\n        pass",
                "expected_behavior": "p = Point(1, 2); p.move(3, 4); assert (p.x, p.y) == (4, 6)",
                "test_cases": [
                    {"test_script": "p = Point(1, 2)\np.move(3, 4)\nassert (p.x, p.y) == (4, 6)"}
                ]
            }
        ]
    },
    {
        "id": "constructors",
        "title": "Constructors",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 38,
        "description": "The __init__ method for initializing object state upon creation.",
        "learning_objectives": "Set up instance attributes during instantiation.",
        "explanation": "The __init__ method is invoked automatically when a new instance is created to set initial attributes.",
        "examples": [{"title": "Constructor", "code": "class User:\n    def __init__(self, username):\n        self.username = username"}],
        "prerequisites": ["objects"],
        "problems": [
            {
                "id": 138,
                "title": "Rectangle Area",
                "description": "Write class Rectangle with __init__(self, width, height) and area(self) returning width * height.",
                "difficulty": "medium",
                "topic": "constructors",
                "starter_code": "class Rectangle:\n    def __init__(self, width, height):\n        pass\n    def area(self):\n        pass",
                "expected_behavior": "r = Rectangle(4, 5); r.area() returns 20",
                "test_cases": [
                    {"test_script": "r = Rectangle(4, 5)\nassert r.area() == 20"}
                ]
            }
        ]
    },
    {
        "id": "inheritance",
        "title": "Inheritance",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 39,
        "description": "Subclassing, method overriding, and super() calls.",
        "learning_objectives": "Derive specialized child classes from common parent abstractions.",
        "explanation": "Inheritance enables a child class to inherit attributes and methods from a parent class, using super() to invoke parent behaviors.",
        "examples": [{"title": "Subclass", "code": "class Animal:\n    pass\nclass Cat(Animal):\n    pass"}],
        "prerequisites": ["constructors"],
        "problems": [
            {
                "id": 139,
                "title": "Square Inherits Rectangle",
                "description": "Write class Square that inherits from Rectangle and takes side in __init__(self, side).",
                "difficulty": "medium",
                "topic": "inheritance",
                "starter_code": "class Rectangle:\n    def __init__(self, width, height):\n        self.width = width\n        self.height = height\n    def area(self):\n        return self.width * self.height\n\nclass Square(Rectangle):\n    def __init__(self, side):\n        pass",
                "expected_behavior": "sq = Square(4); sq.area() returns 16",
                "test_cases": [
                    {"test_script": "sq = Square(4)\nassert sq.area() == 16\nassert isinstance(sq, Rectangle)"}
                ]
            }
        ]
    },
    {
        "id": "iterators",
        "title": "Iterators",
        "category": "Intermediate Python",
        "difficulty": "hard",
        "order_index": 40,
        "description": "The iterator protocol: __iter__() and __next__(), and StopIteration.",
        "learning_objectives": "Implement custom stream iterators following Python's protocol.",
        "explanation": "An iterator is an object that implements __iter__() (returning self) and __next__() (returning the next value or raising StopIteration).",
        "examples": [{"title": "Iterator Protocol", "code": "class Countdown:\n    def __init__(self, n):\n        self.n = n\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.n <= 0: raise StopIteration\n        self.n -= 1; return self.n + 1"}],
        "prerequisites": ["classes"],
        "problems": [
            {
                "id": 140,
                "title": "Custom Range Iterator",
                "description": "Write class RangeIterator(start, stop) returning numbers from start up to (exclusive) stop via __iter__ and __next__.",
                "difficulty": "hard",
                "topic": "iterators",
                "starter_code": "class RangeIterator:\n    def __init__(self, start, stop):\n        pass\n    def __iter__(self):\n        return self\n    def __next__(self):\n        pass",
                "expected_behavior": "list(RangeIterator(1, 4)) returns [1, 2, 3]",
                "test_cases": [
                    {"test_script": "assert list(RangeIterator(1, 4)) == [1, 2, 3]"}
                ]
            }
        ]
    },
    {
        "id": "generators",
        "title": "Generators",
        "category": "Intermediate Python",
        "difficulty": "medium",
        "order_index": 41,
        "description": "Lazy evaluation and state preservation using 'yield'.",
        "learning_objectives": "Construct memory-efficient data streams.",
        "explanation": "Generators are functions that yield values one at a time using 'yield', suspending and resuming their state between calls.",
        "examples": [{"title": "Fibonacci Generator", "code": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b"}],
        "prerequisites": ["iterators"],
        "problems": [
            {
                "id": 141,
                "title": "Even Number Generator",
                "description": "Write even_generator(limit) that yields even numbers from 0 up to limit.",
                "difficulty": "medium",
                "topic": "generators",
                "starter_code": "def even_generator(limit):\n    pass",
                "expected_behavior": "list(even_generator(6)) returns [0, 2, 4, 6]",
                "test_cases": [
                    {"input": [6], "expected": [0, 2, 4, 6]}
                ]
            }
        ]
    },

    # --- PILLAR 4: PROBLEM SOLVING & ALGORITHMS (42-49) ---
    {
        "id": "searching",
        "title": "Searching",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 42,
        "description": "Linear Search O(n) and Binary Search O(log n) on sorted arrays.",
        "learning_objectives": "Implement binary search and recognize when sorted order enables logarithmic time.",
        "explanation": "Binary search repeatedly divides a sorted search interval in half. Comparing the target with the middle element eliminates half the candidates.",
        "examples": [{"title": "Binary Search", "code": "def bin_search(arr, x):\n    low, high = 0, len(arr) - 1"}],
        "prerequisites": ["lists", "while-loops"],
        "problems": [
            {
                "id": 142,
                "title": "Binary Search",
                "description": "Write binary_search(arr, target) returning the index of target in sorted arr, or -1 if absent.",
                "difficulty": "medium",
                "topic": "searching",
                "starter_code": "def binary_search(arr, target):\n    pass",
                "expected_behavior": "binary_search([1, 3, 5, 7, 9], 5) returns 2",
                "test_cases": [
                    {"input": [[1, 3, 5, 7, 9], 5], "expected": 2},
                    {"input": [[1, 3, 5, 7, 9], 4], "expected": -1}
                ]
            }
        ]
    },
    {
        "id": "sorting",
        "title": "Sorting",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 43,
        "description": "Comparison-based sorting (Bubble, Insertion, Merge Sort).",
        "learning_objectives": "Understand in-place vs out-of-place sorting and stability.",
        "explanation": "Sorting orders elements according to a comparator. Bubble sort swaps adjacent inverted pairs; merge sort divides and merges sorted halves in O(n log n).",
        "examples": [{"title": "Bubble Sort", "code": "# repeated swaps"}],
        "prerequisites": ["searching"],
        "problems": [
            {
                "id": 143,
                "title": "Bubble Sort Implementation",
                "description": "Write bubble_sort(arr) that sorts a list of numbers in ascending order without using .sort() or sorted().",
                "difficulty": "medium",
                "topic": "sorting",
                "starter_code": "def bubble_sort(arr):\n    pass",
                "expected_behavior": "bubble_sort([5, 2, 8, 1]) returns [1, 2, 5, 8]",
                "test_cases": [
                    {"input": [[5, 2, 8, 1]], "expected": [1, 2, 5, 8]},
                    {"input": [[]], "expected": []}
                ]
            }
        ]
    },
    {
        "id": "hash-map-problems",
        "title": "Hash-map Problems",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 44,
        "description": "Using hash tables for O(1) lookups to solve two-sum, anagrams, and frequency problems.",
        "learning_objectives": "Trade space for time by caching seen elements in a hash map.",
        "explanation": "Hash maps provide O(1) expected time key lookups. By storing complements or previously seen elements, quadratic brute-force searches can be reduced to linear time.",
        "examples": [{"title": "Two Sum with Map", "code": "seen = {}\nfor i, num in enumerate(arr):\n    comp = target - num\n    if comp in seen: return [seen[comp], i]\n    seen[num] = i"}],
        "prerequisites": ["dictionaries"],
        "problems": [
            {
                "id": 144,
                "title": "Two Sum Fast",
                "description": "Write two_sum_fast(numbers, target) returning a list of the indices [i, j] whose values add to target.",
                "difficulty": "medium",
                "topic": "hash-map-problems",
                "starter_code": "def two_sum_fast(numbers, target):\n    pass",
                "expected_behavior": "two_sum_fast([2, 7, 11, 15], 9) returns [0, 1]",
                "test_cases": [
                    {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]}
                ]
            }
        ]
    },
    {
        "id": "stack",
        "title": "Stack",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 45,
        "description": "Last-In, First-Out (LIFO) data structures and parenthesis matching.",
        "learning_objectives": "Utilize stacks for undo mechanisms, syntax parsing, and depth-first traversals.",
        "explanation": "A stack enforces LIFO ordering. Elements are added with push/append and removed from the top with pop().",
        "examples": [{"title": "Balanced Parentheses", "code": "stack = []\nfor ch in s:\n    if ch == '(': stack.append(ch)\n    elif ch == ')':\n        if not stack: return False\n        stack.pop()"}],
        "prerequisites": ["lists"],
        "problems": [
            {
                "id": 145,
                "title": "Valid Parentheses",
                "description": "Write is_valid_parentheses(s) returning True if brackets ()[]{} are balanced and properly closed.",
                "difficulty": "medium",
                "topic": "stack",
                "starter_code": "def is_valid_parentheses(s):\n    pass",
                "expected_behavior": "is_valid_parentheses('()[]{}') -> True, is_valid_parentheses('(]') -> False",
                "test_cases": [
                    {"input": ["()[]{}"], "expected": True},
                    {"input": ["(]"], "expected": False},
                    {"input": ["([{}])"], "expected": True}
                ]
            }
        ]
    },
    {
        "id": "queue",
        "title": "Queue",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 46,
        "description": "First-In, First-Out (FIFO) data structures and breadth-first pipelines.",
        "learning_objectives": "Model sequential service buffers using collections.deque.",
        "explanation": "A queue enforces FIFO ordering. Elements are inserted at the back and removed from the front.",
        "examples": [{"title": "Queue with Deque", "code": "from collections import deque\nq = deque()\nq.append(1)\nfirst = q.popleft()"}],
        "prerequisites": ["lists"],
        "problems": [
            {
                "id": 146,
                "title": "Recent Counter",
                "description": "Write process_queue_requests(requests) that returns the order in which jobs are completed using FIFO.",
                "difficulty": "medium",
                "topic": "queue",
                "starter_code": "def process_queue_requests(requests):\n    pass",
                "expected_behavior": "process_queue_requests(['task1', 'task2']) returns ['task1', 'task2']",
                "test_cases": [
                    {"input": [["task1", "task2", "task3"]], "expected": ["task1", "task2", "task3"]}
                ]
            }
        ]
    },
    {
        "id": "recursion-problems",
        "title": "Recursion Problems",
        "category": "Problem Solving",
        "difficulty": "hard",
        "order_index": 47,
        "description": "Tower of Hanoi, subsets, permutations, and backtracking.",
        "learning_objectives": "Formulate multi-branch recursive problem breakdowns.",
        "explanation": "Recursive problem solving breaks combinatorial challenges into smaller instances by choosing, exploring, and backtracking.",
        "examples": [{"title": "Recursive Sum", "code": "def rec_sum(arr):\n    return 0 if not arr else arr[0] + rec_sum(arr[1:])"}],
        "prerequisites": ["recursion"],
        "problems": [
            {
                "id": 147,
                "title": "Recursive Power",
                "description": "Write fast_pow(x, n) computing x^n for non-negative integer n using fast exponentiation.",
                "difficulty": "hard",
                "topic": "recursion-problems",
                "starter_code": "def fast_pow(x, n):\n    pass",
                "expected_behavior": "fast_pow(2, 10) returns 1024",
                "test_cases": [
                    {"input": [2, 10], "expected": 1024},
                    {"input": [3, 0], "expected": 1}
                ]
            }
        ]
    },
    {
        "id": "two-pointer",
        "title": "Two-pointer Problems",
        "category": "Problem Solving",
        "difficulty": "medium",
        "order_index": 48,
        "description": "Converging or fast/slow pointer strategies on linear sequences.",
        "learning_objectives": "Optimize linear sequence problems from O(n^2) to O(n) using pointer convergence.",
        "explanation": "Two pointers iterate from both ends toward each other or travel at different speeds to solve partitioned array problems in a single pass.",
        "examples": [{"title": "Two Pointer Palindrome", "code": "left, right = 0, len(s) - 1\nwhile left < right:\n    if s[left] != s[right]: return False\n    left += 1; right -= 1\nreturn True"}],
        "prerequisites": ["while-loops", "slicing"],
        "problems": [
            {
                "id": 148,
                "title": "Two-Pointer Palindrome",
                "description": "Write is_palindrome_fast(s) using two pointers to check if an alphanumeric lowercase string is a palindrome.",
                "difficulty": "medium",
                "topic": "two-pointer",
                "starter_code": "def is_palindrome_fast(s):\n    pass",
                "expected_behavior": "is_palindrome_fast('racecar') returns True; is_palindrome_fast('hello') returns False",
                "test_cases": [
                    {"input": ["racecar"], "expected": True},
                    {"input": ["hello"], "expected": False}
                ]
            }
        ]
    },
    {
        "id": "algorithmic-complexity",
        "title": "Algorithmic Complexity / Big-O",
        "category": "Problem Solving",
        "difficulty": "hard",
        "order_index": 49,
        "description": "Time and Space complexity: O(1), O(log n), O(n), O(n log n), O(n^2).",
        "learning_objectives": "Analyze asymptotic upper bounds and select optimal data structures.",
        "explanation": "Big-O notation describes how execution time or space requirements scale asymptotically as the input size n approaches infinity.",
        "examples": [{"title": "Comparing Complexities", "code": "# O(1) hash lookup vs O(n) linear search"}],
        "prerequisites": ["searching", "sorting", "hash-map-problems"],
        "problems": [
            {
                "id": 149,
                "title": "Identify Duplicate O(n)",
                "description": "Write find_first_duplicate(nums) returning the first value that appears twice using an O(n) hash set lookup, or None.",
                "difficulty": "medium",
                "topic": "algorithmic-complexity",
                "starter_code": "def find_first_duplicate(nums):\n    pass",
                "expected_behavior": "find_first_duplicate([2, 5, 1, 2, 3, 5]) returns 2",
                "test_cases": [
                    {"input": [[2, 5, 1, 2, 3, 5]], "expected": 2},
                    {"input": [[1, 2, 3]], "expected": None}
                ]
            }
        ]
    }
]
