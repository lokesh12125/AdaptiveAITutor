import sqlite3
import json

DATABASE_PATH = "tutor.db"

def expand_curriculum():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all concepts (topics)
    cursor.execute("SELECT id, title FROM concepts")
    concepts = cursor.fetchall()

    # Get max problem ID to avoid collisions
    cursor.execute("SELECT MAX(id) FROM problems")
    max_id = cursor.fetchone()[0] or 1000
    next_id = max_id + 1

    for concept in concepts:
        concept_id = concept["id"]
        title = concept["title"]
        
        # Check existing problems for this concept
        cursor.execute("SELECT difficulty FROM problems WHERE concept_id = ?", (concept_id,))
        existing = [row["difficulty"] for row in cursor.fetchall()]

        difficulties = ["easy", "medium", "hard"]
        for diff in difficulties:
            if diff not in existing:
                # Add a dummy but functional problem for this difficulty
                problem_title = f"{title} - {diff.capitalize()} Challenge"
                desc = f"Solve a {diff} problem related to {title}. Write a function `solve_problem()` that returns '{diff}'."
                starter = "def solve_problem():\n    # TODO: Implement\n    pass"
                expected = f"solve_problem() returns '{diff}'"
                
                tests = json.dumps([
                    {"input": [], "expected": diff}
                ])
                
                cursor.execute("""
                    INSERT INTO problems (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'builtin')
                """, (next_id, problem_title, desc, diff, concept_id, starter, expected, concept_id, tests))
                next_id += 1

    conn.commit()
    conn.close()
    print(f"Curriculum expanded. Next problem ID would be {next_id}.")

if __name__ == "__main__":
    expand_curriculum()
