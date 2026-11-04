"""Optional OpenAI enrichment with strict timeout and rich Socratic pedagogical fallbacks."""
import logging
import re
from openai import OpenAI
from typing import Any, Dict, Optional
from ..config import OPENAI_API_KEY, OPENAI_MODEL, api_key_configured

logger = logging.getLogger("tutor.llm")


def generate_contextual_socratic_fallback(
    message: str,
    problem: Optional[Dict[str, Any]] = None,
    learner_state: Optional[Dict[str, Any]] = None
) -> str:
    """
    Produce rich, pedagogically sound, topic-specific Socratic guidance
    even when running in demo mode or when the external LLM provider is unavailable.
    """
    msg_lower = (message or "").strip().lower()
    prob_title = problem.get("title", "") if problem else ""
    prob_topic = (problem.get("topic") or problem.get("concept_id") or "") if problem else ""
    expected = problem.get("expected_behavior", "") if problem else ""

    # 1. Greetings / Introductory intent
    if re.search(r"\b(hi|hello|hey|greetings|morning|afternoon|evening)\b", msg_lower) and len(msg_lower.split()) <= 4:
        if prob_title:
            return (
                f"Hello! I'm your Socratic Python AI Tutor. We're currently working on **{prob_title}** ({prob_topic}). "
                "Feel free to ask me for conceptual hints, debugging guidance, or explanations of any Python syntax!"
            )
        return (
            "Hello! I'm your Socratic Python AI Tutor. Ask me any Python question—from fundamental syntax "
            "like loops and lists to algorithm design, debugging tips, or time complexity analysis!"
        )

    # 2. Gratitude / Acknowledgment
    if re.search(r"\b(thank|thanks|great|cool|awesome|understood|got it)\b", msg_lower) and len(msg_lower.split()) <= 4:
        return "You're very welcome! Keep up the great practice. What would you like to explore or solve next?"

    # 3. Off-topic questions (e.g., weather, politics, non-programming trivia)
    non_programming_keywords = ["weather", "president", "capital of", "recipe", "song", "movie", "celebrity"]
    if any(k in msg_lower for k in non_programming_keywords):
        return (
            "I'm dedicated as your specialized Python & Computer Science Tutor. Let's focus our conversation on "
            "programming concepts, data structures, debugging code, or solving your coding challenges! "
            "What Python topic can I help you understand?"
        )

    # 4. Problem-Specific Hints & Guidance ("how to solve", "give me a hint", "stuck")
    if prob_title and any(k in msg_lower for k in ["hint", "stuck", "how to solve", "start", "clue", "help with this problem", "where do i begin"]):
        if "sum" in prob_title.lower() or "sum" in prob_topic.lower():
            return (
                f"For **{prob_title}**, think about the accumulation pattern:\n\n"
                "1. **Initial state:** How should your running total start (e.g. before examining any elements)?\n"
                "2. **Iteration:** As you traverse the sequence, how do you update that running total?\n"
                "3. **Termination:** Make sure your return statement executes *after* the loop finishes, not inside it!\n\n"
                f"*Expected Target:* `{expected}`"
            )
        if "max" in prob_title.lower() or "largest" in prob_title.lower():
            return (
                f"For **{prob_title}**, consider how to track the best candidate seen so far:\n\n"
                "1. What is a safe starting value for `max_val`? (Hint: using the first element `numbers[0]` is safer than `0` if numbers can be negative).\n"
                "2. As you iterate through the list, what condition triggers updating `max_val`?\n"
                "3. Return the maximum once all items have been inspected."
            )
        if "vowel" in prob_title.lower():
            return (
                f"For **{prob_title}**:\n\n"
                "1. How can you define the vowels set? (e.g., `vowels = 'aeiouAEIOU'`).\n"
                "2. How do you check membership in Python? (`if char in vowels:`).\n"
                "3. Keep a counter variable that increments by 1 for each match."
            )
        if "palindrome" in prob_title.lower():
            return (
                f"For **{prob_title}**:\n\n"
                "1. Notice the case and spacing constraints: convert to a uniform case (`.lower()`) and remove non-alphanumeric characters or spaces (`.replace(' ', '')`).\n"
                "2. How can you compare the cleaned string to its reverse in Python? (Hint: slicing syntax `s[::-1]` reverses a string efficiently)."
            )
        if "two sum" in prob_title.lower() or "pair" in prob_title.lower():
            return (
                f"For **{prob_title}**:\n\n"
                "1. **Target relationship:** For any current number `num`, the required complement is `complement = target - num`.\n"
                "2. **Optimal structure:** A Python dictionary can store each previously seen number and its index: `{number: index}`.\n"
                "3. If `complement` is already in your dictionary, you've found the answer in $O(n)$ time!"
            )
        return (
            f"Here is a Socratic clue for **{prob_title}**:\n\n"
            f"- **Problem Goal:** {expected}\n"
            "- Break the algorithm into three steps: **Input preparation**, **core loop/transformation**, and **return value**.\n"
            "- Ask yourself: What data structure best represents the intermediate state?"
        )

    # 5. Conceptual Inquiries
    if "list comprehension" in msg_lower:
        return (
            "### Python List Comprehensions\n\n"
            "List comprehensions provide a concise way to create lists based on existing iterables:\n\n"
            "```python\n"
            "# Syntax: [expression for item in iterable if condition]\n"
            "squares = [x**2 for x in range(1, 6)]           # [1, 4, 9, 16, 25]\n"
            "even_squares = [x**2 for x in range(1, 6) if x % 2 == 0]  # [4, 16]\n"
            "```\n\n"
            "**Key benefit:** They are more readable and often faster than traditional `for` loops appending to an empty list."
        )

    if any(k in msg_lower for k in ["dictionary", "dict", "hash map", "key value"]):
        return (
            "### Python Dictionaries (`dict`)\n\n"
            "Dictionaries store associations between unique **keys** and **values** with average $O(1)$ lookup time:\n\n"
            "```python\n"
            "student_scores = {'Alice': 95, 'Bob': 88}\n"
            "\n"
            "# Safe access using .get() (avoids KeyError):\n"
            "score = student_scores.get('Charlie', 0)  # Returns default 0\n"
            "\n"
            "# Iterating keys and values:\n"
            "for name, score in student_scores.items():\n"
            "    print(f'{name}: {score}')\n"
            "```\n\n"
            "**Pro Tip:** Use `.get(key, default)` when accessing keys that might not exist to prevent runtime `KeyError` crashes."
        )

    if any(k in msg_lower for k in ["loop", "for loop", "while loop", "iteration"]):
        return (
            "### Python Loops & Iteration Patterns\n\n"
            "Python offers two primary loop constructs:\n\n"
            "1. **`for` loop (definite iteration):** Best when traversing sequences or ranges.\n"
            "```python\n"
            "for i in range(len(items)):\n"
            "    print(i, items[i])\n"
            "# Or idiomatic enumerate:\n"
            "for index, value in enumerate(items):\n"
            "    print(index, value)\n"
            "```\n\n"
            "2. **`while` loop (indefinite iteration):** Continues as long as a boolean condition holds.\n"
            "```python\n"
            "while left < right:\n"
            "    # always ensure condition moves toward termination!\n"
            "    left += 1\n"
            "```\n\n"
            "**Common trap:** Avoid placing a `return` statement directly inside the loop on the first iteration unless you intentionally intend to exit early."
        )

    if any(k in msg_lower for k in ["recursion", "recursive", "base case"]):
        return (
            "### Recursion in Python\n\n"
            "A recursive function solves a problem by calling itself on smaller instances of the same problem. Every recursive function requires two essential parts:\n\n"
            "1. **Base Case:** A stopping condition that returns immediately without recursing (prevents `RecursionError`).\n"
            "2. **Recursive Step:** Breaking the problem down and moving closer to the base case.\n\n"
            "```python\n"
            "def factorial(n):\n"
            "    if n <= 1:        # 1. Base case\n"
            "        return 1\n"
            "    return n * factorial(n - 1)  # 2. Recursive step\n"
            "```\n\n"
            "**Socratic Question:** In your current challenge, what is the smallest possible input where the answer is immediately known?"
        )

    if any(k in msg_lower for k in ["big-o", "time complexity", "space complexity", "efficiency"]):
        return (
            "### Computational Complexity (Big-O Notation)\n\n"
            "Big-O measures how runtime or memory usage scales as the input size $n$ grows:\n\n"
            "- **$O(1)$ Constant Time:** Direct dictionary lookup, list index access (`arr[i]`).\n"
            "- **$O(n)$ Linear Time:** Single loop traversing $n$ items, `sum(arr)`, `max(arr)`.\n"
            "- **$O(n \\log n)$:** Efficient sorting algorithms (Python's `Timsort` via `sorted()`).\n"
            "- **$O(n^2)$ Quadratic Time:** Nested loops comparing every pair of elements.\n\n"
            "**Optimization Goal:** When solving search/pair problems, substituting a nested loop ($O(n^2)$) with a dictionary lookup ($O(1)$) reduces overall complexity to $O(n)$."
        )

    if any(k in msg_lower for k in ["indexerror", "out of range", "index"]):
        return (
            "### Debugging `IndexError: list index out of range`\n\n"
            "This error occurs when accessing an index that doesn't exist in the sequence:\n\n"
            "- Remember Python uses **0-based indexing**: A list of length 5 has valid indices `0, 1, 2, 3, 4`.\n"
            "- Accessing `arr[len(arr)]` triggers an `IndexError` because the maximum index is `len(arr) - 1`.\n"
            "- **Fix:** Use `range(len(arr))` or iterate over elements directly (`for item in arr:`)."
        )

    if any(k in msg_lower for k in ["typeerror", "unsupported operand"]):
        return (
            "### Debugging `TypeError`\n\n"
            "A `TypeError` means an operation was attempted on incompatible data types (e.g. adding a string to an integer `10 + '5'`):\n\n"
            "- Check variable types using `type(x)` or `isinstance(x, int)`.\n"
            "- Perform explicit casting where needed: `int('5')` or `str(10)`.\n"
            "- Make sure functions return the expected data type specified in the problem statement."
        )

    # General Socratic fallback
    return (
        f"In Python, clean problem-solving starts with breaking requirements into small invariant steps. "
        f"{f'For {prob_title}, review the expected behavior: `{expected}`. ' if prob_title else ''}"
        "Try isolating the simplest test case (e.g., empty input or length 1), and trace how your variables transform step-by-step. "
        "What specific behavior or error are you observing?"
    )


class TutorLLM:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=8.0) if api_key_configured() else None
        self.mode = "live" if self._client else "demo"
        self.last_was_fallback = not bool(self._client)

    def tutor_reply(self, prompt: str, fallback: str, system_prompt: Optional[str] = None) -> str:
        if not self._client or self.mode == "demo":
            self.last_was_fallback = True
            return fallback
        sys_msg = system_prompt or "You are a concise Python tutor. Give a Socratic hint; never provide a complete solution."
        try:
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                timeout=8.0,
            )
            text = response.choices[0].message.content.strip()
            if text:
                self.last_was_fallback = False
                return text
        except Exception as err:
            logger.warning("LLM request failed or timed out: %s. Degrading to demo mode.", type(err).__name__)
            self.mode = "demo"
            self._client = None
            self.last_was_fallback = True
        return fallback


llm = TutorLLM()

