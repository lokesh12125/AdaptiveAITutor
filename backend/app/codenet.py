"""IBM Project CodeNet integration module providing authentic curated programming challenges, reference solutions, and common error patterns."""
import json
from pathlib import Path

# Curated practical subset derived from IBM Project CodeNet (https://github.com/IBM/Project_CodeNet)
# Each record includes problem metadata, input/output format, tests, accepted solution, and buggy submission examples.
CODENET_PROBLEMS = [
    {
        "id": 201,
        "codenet_id": "p00000",
        "title": "QQ (Multiplication Table)",
        "difficulty": "easy",
        "topic": "for-loops",
        "concept_id": "for-loops",
        "source": "IBM-Project-CodeNet",
        "description": "Write generate_multiplication_table() that returns a list of formatted strings '<i乘x> = <val>' for 1<=i<=9 and 1<=j<=9. (Format: f'{i}x{j}={i*j}').",
        "starter_code": "def generate_multiplication_table():\n    # Generate list of 'ixj=val' for i in 1..9, j in 1..9\n    pass",
        "expected_behavior": "Returns 81 multiplication entries starting with '1x1=1' and ending with '9x9=81'",
        "test_cases": [
            {
                "test_script": "table = generate_multiplication_table()\nassert len(table) == 81\nassert table[0] == '1x1=1'\nassert table[-1] == '9x9=81'\nassert table[8] == '1x9=9'"
            }
        ],
        "accepted_solution": "def generate_multiplication_table():\n    return [f'{i}x{j}={i*j}' for i in range(1, 10) for j in range(1, 10)]",
        "common_incorrect_submission": "def generate_multiplication_table():\n    # Off-by-one error: range(1, 9) instead of range(1, 10)\n    return [f'{i}x{j}={i*j}' for i in range(1, 9) for j in range(1, 9)]",
        "misconception": "Range upper bound off-by-one omission (range(1, 9) stops at 8)."
    },
    {
        "id": 202,
        "codenet_id": "p00001",
        "title": "List of Top 3 Hills",
        "difficulty": "easy",
        "topic": "sorting",
        "concept_id": "sorting",
        "source": "IBM-Project-CodeNet",
        "description": "Write top_three_heights(heights) returning the top 3 highest hills in descending order from a list of hill heights.",
        "starter_code": "def top_three_heights(heights):\n    pass",
        "expected_behavior": "top_three_heights([1819, 2003, 876, 2840, 1720]) returns [2840, 2003, 1819]",
        "test_cases": [
            {"input": [[1819, 2003, 876, 2840, 1720]], "expected": [2840, 2003, 1819]},
            {"input": [[100, 200, 300]], "expected": [300, 200, 100]}
        ],
        "accepted_solution": "def top_three_heights(heights):\n    return sorted(heights, reverse=True)[:3]",
        "common_incorrect_submission": "def top_three_heights(heights):\n    return sorted(heights)[:3]",
        "misconception": "Sorting in ascending rather than descending order."
    },
    {
        "id": 203,
        "codenet_id": "p00002",
        "title": "Digit Number of Sum",
        "difficulty": "easy",
        "topic": "strings",
        "concept_id": "strings",
        "source": "IBM-Project-CodeNet",
        "description": "Write sum_digit_count(a, b) returning the number of digits in the sum (a + b).",
        "starter_code": "def sum_digit_count(a, b):\n    pass",
        "expected_behavior": "sum_digit_count(5, 7) returns 2 (since 5+7=12, which has 2 digits)",
        "test_cases": [
            {"input": [5, 7], "expected": 2},
            {"input": [200, 300], "expected": 3},
            {"input": [0, 0], "expected": 1}
        ],
        "accepted_solution": "def sum_digit_count(a, b):\n    return len(str(a + b))",
        "common_incorrect_submission": "def sum_digit_count(a, b):\n    return len(str(a)) + len(str(b))",
        "misconception": "Summing digit counts of inputs rather than finding the digit count of the sum."
    },
    {
        "id": 204,
        "codenet_id": "p02256",
        "title": "Greatest Common Divisor (Euclid)",
        "difficulty": "medium",
        "topic": "recursion",
        "concept_id": "recursion",
        "source": "IBM-Project-CodeNet",
        "description": "Write gcd_euclid(x, y) computing the greatest common divisor of positive integers x and y using the Euclidean algorithm.",
        "starter_code": "def gcd_euclid(x, y):\n    pass",
        "expected_behavior": "gcd_euclid(147, 105) returns 21",
        "test_cases": [
            {"input": [147, 105], "expected": 21},
            {"input": [54, 24], "expected": 6},
            {"input": [13, 7], "expected": 1}
        ],
        "accepted_solution": "def gcd_euclid(x, y):\n    while y:\n        x, y = y, x % y\n    return x",
        "common_incorrect_submission": "def gcd_euclid(x, y):\n    if y == 0: return x\n    return gcd_euclid(x, x % y)",
        "misconception": "Passing wrong arguments to recursive call (x, x % y instead of y, x % y)."
    },
    {
        "id": 205,
        "codenet_id": "p02257",
        "title": "Prime Numbers Count",
        "difficulty": "medium",
        "topic": "searching",
        "concept_id": "searching",
        "source": "IBM-Project-CodeNet",
        "description": "Write count_primes(numbers) returning the count of prime numbers present in the list numbers.",
        "starter_code": "def count_primes(numbers):\n    pass",
        "expected_behavior": "count_primes([2, 3, 4, 5, 6, 7]) returns 4",
        "test_cases": [
            {"input": [[2, 3, 4, 5, 6, 7]], "expected": 4},
            {"input": [[1, 4, 6, 8, 9]], "expected": 0}
        ],
        "accepted_solution": "def count_primes(numbers):\n    def is_prime(n):\n        if n < 2: return False\n        for i in range(2, int(n**0.5) + 1):\n            if n % i == 0: return False\n        return True\n    return sum(1 for n in numbers if is_prime(n))",
        "common_incorrect_submission": "def count_primes(numbers):\n    # Treats 1 as prime\n    return sum(1 for n in numbers if n > 0 and (n == 2 or n % 2 != 0))",
        "misconception": "Assuming 1 is prime or odd numbers are always prime."
    }
]


def get_codenet_subset() -> list[dict]:
    """Return the curated subset of IBM Project CodeNet problems with metadata."""
    return CODENET_PROBLEMS
