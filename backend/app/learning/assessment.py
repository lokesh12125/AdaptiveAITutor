"""Diagnostic Placement & Pre/Post Assessment Module (R-24, F-01).

Calibrates learner's initial knowledge state P(L0) per concept area rather than assigning a generic flat 0.20 prior.
"""
from typing import Any, Dict, List

PLACEMENT_QUESTIONS = [
    {
        "id": "q1_variables",
        "concept_id": "variables",
        "category": "Foundations",
        "question": "What is the output of the following Python snippet?\nx = 5\ny = x\nx = 10\nprint(y)",
        "options": ["10", "5", "None", "Error"],
        "correct_answer": "5",
        "explanation": "Integers are immutable in Python; y references the original value 5."
    },
    {
        "id": "q2_conditionals",
        "concept_id": "if-statements",
        "category": "Foundations",
        "question": "Which block executes when score = 75?\nif score >= 90: print('A')\nelif score >= 70: print('B')\nelse: print('C')",
        "options": ["A", "B", "C", "None"],
        "correct_answer": "B",
        "explanation": "75 is < 90 but >= 70, so the elif branch executes."
    },
    {
        "id": "q3_loops",
        "concept_id": "for-loops",
        "category": "Foundations",
        "question": "How many numbers are printed by: for i in range(1, 5): print(i)?",
        "options": ["4 (1, 2, 3, 4)", "5 (1, 2, 3, 4, 5)", "3 (2, 3, 4)", "Infinite"],
        "correct_answer": "4 (1, 2, 3, 4)",
        "explanation": "range(start, stop) excludes the stop value, running for 1, 2, 3, 4."
    },
    {
        "id": "q4_functions",
        "concept_id": "functions",
        "category": "Foundations",
        "question": "What does a function in Python return if no return statement is specified?",
        "options": ["0", "False", "None", "Empty string"],
        "correct_answer": "None",
        "explanation": "Python functions implicitly return None if no explicit return is executed."
    },
    {
        "id": "q5_lists",
        "concept_id": "lists",
        "category": "Collections",
        "question": "What does lst[-1] evaluate to for lst = [10, 20, 30]?",
        "options": ["10", "20", "30", "IndexError"],
        "correct_answer": "30",
        "explanation": "Negative indexing in Python accesses elements from the end; -1 is the last item."
    },
    {
        "id": "q6_dicts",
        "concept_id": "dictionaries",
        "category": "Collections",
        "question": "How do you access the value associated with key 'age' in person = {'name': 'Sam', 'age': 25}?",
        "options": ["person['age']", "person(age)", "person.get_index(1)", "person[1]"],
        "correct_answer": "person['age']",
        "explanation": "Dictionary keys are indexed via subscript syntax person['key'] or person.get('key')."
    }
]


def get_placement_quiz() -> List[Dict[str, Any]]:
    """Return placement assessment items with question prompts and choices (without answers)."""
    return [
        {
            "id": q["id"],
            "concept_id": q["concept_id"],
            "category": q["category"],
            "question": q["question"],
            "options": q["options"]
        }
        for q in PLACEMENT_QUESTIONS
    ]


def evaluate_placement_answers(answers: Dict[str, str]) -> Dict[str, Any]:
    """Grade placement answers and compute calibrated concept priors."""
    total = len(PLACEMENT_QUESTIONS)
    correct_count = 0
    concept_scores: Dict[str, float] = {}

    for q in PLACEMENT_QUESTIONS:
        qid = q["id"]
        cid = q["concept_id"]
        user_ans = answers.get(qid, "").strip()
        is_correct = (user_ans == q["correct_answer"])
        if is_correct:
            correct_count += 1
            concept_scores[cid] = 0.70  # Proficient initial prior
        else:
            concept_scores[cid] = 0.20  # Novice standard prior

    overall_score = round(correct_count / max(1, total), 2)
    starting_tier = "advanced" if overall_score >= 0.80 else ("intermediate" if overall_score >= 0.50 else "beginner")

    return {
        "total_questions": total,
        "correct_answers": correct_count,
        "score": overall_score,
        "starting_tier": starting_tier,
        "concept_priors": concept_scores
    }

