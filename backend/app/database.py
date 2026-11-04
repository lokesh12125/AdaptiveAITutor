"""Authoritative SQLite database layer for structured tutoring platform data."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .config import DATABASE_PATH
from .curriculum import CURRICULUM_CONCEPTS
from .codenet import get_codenet_subset

INITIAL_PROBLEMS = [
    (
        1,
        "Sum of an Array",
        "### Problem Statement\nWrite a function `sum_array(numbers)` that calculates and returns the arithmetic sum of all numbers in the given list.\n\n### Input / Output Specifications\n- **Input:** `numbers` (List[int | float]) — A list of numeric values.\n- **Output:** (int | float) — The sum of all elements. Returns 0 if the list is empty.\n\n### Constraints\n- `0 <= len(numbers) <= 10^4`\n- `-10^6 <= numbers[i] <= 10^6`\n\n### Examples\n**Example 1:**\n- Input: `[2, 3, 5]`\n- Output: `10`\n\n**Example 2:**\n- Input: `[]`\n- Output: `0`",
        "easy",
        "lists",
        "def sum_array(numbers):\n    # write your code here\n    pass",
        "sum_array([2, 3, 5]) returns 10",
        "lists",
        json.dumps([{"input": [[2, 3, 5]], "expected": 10}, {"input": [[]], "expected": 0}, {"input": [[-1, 1, 0]], "expected": 0}, {"input": [[42]], "expected": 42}]),
        0,
        None,
        "builtin"
    ),
    (
        2,
        "Maximum Element",
        "### Problem Statement\nWrite a function `find_max(numbers)` that returns the largest numeric value in a non-empty list.\n\n### Input / Output Specifications\n- **Input:** `numbers` (List[int | float]) — A non-empty list of numbers.\n- **Output:** (int | float) — The maximum value in the list.\n\n### Constraints\n- `1 <= len(numbers) <= 10^5`\n- `-10^6 <= numbers[i] <= 10^6`\n\n### Examples\n**Example 1:**\n- Input: `[4, 1, 9]`\n- Output: `9`\n\n**Example 2:**\n- Input: `[-5, -2, -8]`\n- Output: `-2`",
        "easy",
        "lists",
        "def find_max(numbers):\n    # write your code here\n    pass",
        "find_max([4, 1, 9]) returns 9",
        "lists",
        json.dumps([{"input": [[4, 1, 9]], "expected": 9}, {"input": [[-5, -2, -8]], "expected": -2}, {"input": [[100]], "expected": 100}, {"input": [[3, 3, 3]], "expected": 3}]),
        0,
        None,
        "builtin"
    ),
    (
        3,
        "Count Vowels",
        "### Problem Statement\nWrite a function `count_vowels(text)` that counts the total occurrences of vowels (`a`, `e`, `i`, `o`, `u`, case-insensitive) in the given string `text`.\n\n### Input / Output Specifications\n- **Input:** `text` (str) — An input string.\n- **Output:** (int) — Number of vowels found.\n\n### Constraints\n- `0 <= len(text) <= 10^5`\n\n### Examples\n**Example 1:**\n- Input: `'Education'`\n- Output: `5`\n\n**Example 2:**\n- Input: `'sky'`\n- Output: `0`",
        "easy",
        "strings",
        "def count_vowels(text):\n    # write your code here\n    pass",
        "count_vowels('Education') returns 5",
        "strings",
        json.dumps([{"input": ["Education"], "expected": 5}, {"input": ["sky"], "expected": 0}, {"input": [""], "expected": 0}, {"input": ["AEIOUaeiou"], "expected": 10}]),
        0,
        None,
        "builtin"
    ),
    (
        4,
        "Check Palindrome",
        "### Problem Statement\nWrite a function `is_palindrome(text)` that checks whether a given string is a palindrome, ignoring differences in casing and spaces.\n\n### Input / Output Specifications\n- **Input:** `text` (str) — An input string.\n- **Output:** (bool) — `True` if palindrome, `False` otherwise.\n\n### Constraints\n- `0 <= len(text) <= 10^5`\n\n### Examples\n**Example 1:**\n- Input: `'Never odd or even'`\n- Output: `True`\n\n**Example 2:**\n- Input: `'Python'`\n- Output: `False`",
        "medium",
        "strings",
        "def is_palindrome(text):\n    # write your code here\n    pass",
        "is_palindrome('Never odd or even') returns True",
        "strings",
        json.dumps([{"input": ["Never odd or even"], "expected": True}, {"input": ["Python"], "expected": False}, {"input": ["Racecar"], "expected": True}, {"input": [""], "expected": True}]),
        0,
        None,
        "builtin"
    ),
    (
        5,
        "Two Sum",
        "### Problem Statement\nWrite a function `two_sum(numbers, target)` returning the 0-based indices `[i, j]` ($i < j$) of two distinct numbers in `numbers` that add up to `target`. If no such pair exists, return `None`.\n\n### Input / Output Specifications\n- **Input:** `numbers` (List[int]), `target` (int)\n- **Output:** (List[int] | None) — Two indices `[i, j]` or `None`.\n\n### Constraints\n- `2 <= len(numbers) <= 10^4`\n\n### Examples\n**Example 1:**\n- Input: `[2, 7, 11, 15]`, target: `9`\n- Output: `[0, 1]`\n\n**Example 2:**\n- Input: `[3, 2, 4]`, target: `6`\n- Output: `[1, 2]`",
        "medium",
        "arrays",
        "def two_sum(numbers, target):\n    # write your code here\n    pass",
        "two_sum([2, 7, 11, 15], 9) returns [0, 1]",
        "hash-map-problems",
        json.dumps([{"input": [[2, 7, 11, 15], 9], "expected": [0, 1]}, {"input": [[3, 2, 4], 6], "expected": [1, 2]}, {"input": [[1, 2, 3], 10], "expected": None}, {"input": [[3, 3], 6], "expected": [0, 1]}]),
        0,
        None,
        "builtin"
    ),
]


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _safe_add_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    col_name = column_def.strip().split()[0]
    cursor = conn.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in cursor.fetchall()]
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def initialize_database() -> None:
    with connection() as conn:
        # P-11/S-02: Enable Write-Ahead Logging (WAL) for concurrent read/write and set busy timeout
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
        except Exception:
            pass
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learners (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            description TEXT NOT NULL,
            learning_objectives TEXT NOT NULL,
            explanation TEXT NOT NULL,
            examples_json TEXT NOT NULL,
            prerequisites_json TEXT NOT NULL,
            order_index INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            difficulty TEXT,
            topic TEXT,
            starter_code TEXT,
            expected_behavior TEXT,
            concept_id TEXT,
            test_cases_json TEXT,
            is_custom INTEGER DEFAULT 0,
            creator_id TEXT,
            source TEXT DEFAULT 'builtin'
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT,
            problem_id INTEGER,
            code TEXT,
            passed INTEGER,
            error_type TEXT,
            created_at TEXT,
            concept_id TEXT,
            response_time REAL DEFAULT 0,
            scaffolding_level INTEGER DEFAULT 1,
            hints_used INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS learner_states (
            learner_id TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS concept_progress (
            learner_id TEXT,
            concept_id TEXT,
            mastery REAL DEFAULT 0.35,
            attempts_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            last_attempt_at TEXT,
            status TEXT DEFAULT 'unlocked',
            PRIMARY KEY (learner_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            problem_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS hints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            problem_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            hint_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            problem_id INTEGER,
            concept_id TEXT,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS custom_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            concept_id TEXT,
            difficulty TEXT NOT NULL,
            starter_code TEXT,
            test_cases_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learning_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            problems_attempted INTEGER DEFAULT 0,
            problems_solved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS evaluation_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            learning_gain REAL DEFAULT 0,
            hint_efficiency REAL DEFAULT 0,
            avg_hints_per_problem REAL DEFAULT 0,
            task_completion_rate REAL DEFAULT 0,
            time_to_completion REAL DEFAULT 0,
            satisfaction_score INTEGER,
            recorded_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS historical_learners (
            id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            intervention TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS state_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            problem_id INTEGER,
            concept_id TEXT,
            mastery REAL NOT NULL,
            confidence REAL NOT NULL,
            confusion REAL NOT NULL,
            cognitive_load REAL NOT NULL,
            consecutive_fails INTEGER DEFAULT 0,
            scaffolding_level INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learner_misconceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            concept_id TEXT NOT NULL,
            misconception_code TEXT NOT NULL,
            error_type TEXT,
            occurrence_count INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL,
            resolved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS reflection_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            learner_id TEXT NOT NULL,
            problem_id INTEGER,
            prompt_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            quality_score REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS satisfaction_surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            session_id INTEGER,
            usefulness_score INTEGER DEFAULT 5,
            clarity_score INTEGER DEFAULT 5,
            hint_adequacy_score INTEGER DEFAULT 5,
            perceived_adaptivity_score INTEGER DEFAULT 5,
            comments TEXT,
            recorded_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS classes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            teacher_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS class_enrolments (
            class_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            enrolled_at TEXT NOT NULL,
            PRIMARY KEY (class_id, student_id)
        );
        CREATE INDEX IF NOT EXISTS idx_attempts_learner_time ON attempts(learner_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_state_history_learner ON state_history(learner_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_misconceptions_learner ON learner_misconceptions(learner_id, concept_id);
        """)

        # Run non-destructive column migrations on existing tables if needed
        _safe_add_column(conn, "users", "role TEXT DEFAULT 'student'")
        _safe_add_column(conn, "problems", "concept_id TEXT")
        _safe_add_column(conn, "problems", "test_cases_json TEXT")
        _safe_add_column(conn, "problems", "is_custom INTEGER DEFAULT 0")
        _safe_add_column(conn, "problems", "creator_id TEXT")
        _safe_add_column(conn, "problems", "source TEXT DEFAULT 'builtin'")
        _safe_add_column(conn, "attempts", "concept_id TEXT")
        _safe_add_column(conn, "attempts", "response_time REAL DEFAULT 0")
        _safe_add_column(conn, "attempts", "scaffolding_level INTEGER DEFAULT 1")
        _safe_add_column(conn, "attempts", "hints_used INTEGER DEFAULT 0")
        _safe_add_column(conn, "concept_progress", "confidence REAL DEFAULT 0.5")
        _safe_add_column(conn, "concept_progress", "confusion REAL DEFAULT 0.0")
        _safe_add_column(conn, "concept_progress", "cognitive_load REAL DEFAULT 0.0")
        _safe_add_column(conn, "concept_progress", "hints_used INTEGER DEFAULT 0")
        _safe_add_column(conn, "hints", "focus TEXT DEFAULT 'Conceptual'")

        # Seed initial built-in problems non-destructively
        conn.executemany("""
            INSERT INTO problems 
            (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                difficulty = excluded.difficulty,
                topic = excluded.topic,
                starter_code = excluded.starter_code,
                expected_behavior = excluded.expected_behavior,
                concept_id = excluded.concept_id,
                test_cases_json = excluded.test_cases_json,
                source = excluded.source
            WHERE problems.is_custom = 0 OR problems.is_custom IS NULL
        """, INITIAL_PROBLEMS)

        # Seed 49 curriculum concepts and associated problems non-destructively
        for concept in CURRICULUM_CONCEPTS:
            conn.execute("""
                INSERT INTO concepts 
                (id, title, category, difficulty, description, learning_objectives, explanation, examples_json, prerequisites_json, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    difficulty = excluded.difficulty,
                    description = excluded.description,
                    learning_objectives = excluded.learning_objectives,
                    explanation = excluded.explanation,
                    examples_json = excluded.examples_json,
                    prerequisites_json = excluded.prerequisites_json,
                    order_index = excluded.order_index
            """, (
                concept["id"],
                concept["title"],
                concept["category"],
                concept["difficulty"],
                concept["description"],
                concept["learning_objectives"],
                concept["explanation"],
                json.dumps(concept.get("examples", [])),
                json.dumps(concept.get("prerequisites", [])),
                concept["order_index"]
            ))
            for prob in concept.get("problems", []):
                conn.execute("""
                    INSERT INTO problems
                    (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 'curriculum')
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        description = excluded.description,
                        difficulty = excluded.difficulty,
                        topic = excluded.topic,
                        starter_code = excluded.starter_code,
                        expected_behavior = excluded.expected_behavior,
                        concept_id = excluded.concept_id,
                        test_cases_json = excluded.test_cases_json,
                        source = excluded.source
                    WHERE problems.is_custom = 0 OR problems.is_custom IS NULL
                """, (
                    prob["id"],
                    prob["title"],
                    prob["description"],
                    prob["difficulty"],
                    prob["topic"],
                    prob["starter_code"],
                    prob["expected_behavior"],
                    concept["id"],
                    json.dumps(prob.get("test_cases", []))
                ))

        # Seed IBM Project CodeNet subset problems non-destructively
        for cp in get_codenet_subset():
            conn.execute("""
                INSERT INTO problems
                (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    difficulty = excluded.difficulty,
                    topic = excluded.topic,
                    starter_code = excluded.starter_code,
                    expected_behavior = excluded.expected_behavior,
                    concept_id = excluded.concept_id,
                    test_cases_json = excluded.test_cases_json,
                    source = excluded.source
                WHERE problems.is_custom = 0 OR problems.is_custom IS NULL
            """, (
                cp["id"],
                cp["title"],
                cp["description"],
                cp["difficulty"],
                cp["topic"],
                cp["starter_code"],
                cp["expected_behavior"],
                cp.get("concept_id", cp["topic"]),
                json.dumps(cp.get("test_cases", [])),
                cp.get("source", "IBM-Project-CodeNet")
            ))

        # Seed default historical learners with consistent 8D vectors non-destructively
        default_demos = [
            ("synthetic-1", [0.25, 0.30, 0.75, 0.70, 0.15, 0.80, 0.70, 0.40], "Break down syntax rules, isolate the offending line, and check matching delimiters."),
            ("synthetic-2", [0.55, 0.50, 0.45, 0.40, 0.50, 0.40, 0.35, 0.30], "Provide pseudocode structure and prompt tracing on small sample inputs."),
            ("synthetic-3", [0.85, 0.80, 0.15, 0.20, 0.85, 0.10, 0.10, 0.20], "Challenge with edge cases and prompt explanation of algorithmic time complexity.")
        ]
        conn.executemany("""
            INSERT INTO historical_learners (id, profile_json, intervention) 
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                profile_json = excluded.profile_json,
                intervention = excluded.intervention
        """, [(k, json.dumps(v), inter) for k, v, inter in default_demos])

        # Seed default student and teacher demo accounts
        from .auth import hash_password
        default_accounts = [
            ("user-demo-student", "Demo Student", "demo@student.edu", "demo123", "student"),
            ("user-demo-teacher", "Demo Teacher", "teacher@adaptive.edu", "teacher123", "teacher")
        ]
        now = datetime.now(timezone.utc).isoformat()
        for u_id, u_name, u_email, u_pwd, u_role in default_accounts:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (u_email,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (u_id, u_name, u_email, hash_password(u_pwd), u_role, now)
                )
                conn.execute("INSERT OR IGNORE INTO learners VALUES (?, ?)", (u_id, u_name))
            else:
                conn.execute(
                    "UPDATE users SET password_hash = ?, role = ? WHERE email = ?",
                    (hash_password(u_pwd), u_role, u_email)
                )

        # Seed initial demo state and metrics if missing
        demo_student_state = conn.execute("SELECT learner_id FROM learner_states WHERE learner_id = 'user-demo-student'").fetchone()
        if not demo_student_state:
            initial_state = {
                "mastery": 0.42,
                "confidence": 0.65,
                "confusion": 0.12,
                "cognitive_load": 0.28,
                "progress": 0.25,
                "hints_used": 1
            }
            conn.execute(
                "INSERT INTO learner_states (learner_id, state_json, updated_at) VALUES (?, ?, ?)",
                ("user-demo-student", json.dumps(initial_state), now)
            )

        demo_metric = conn.execute("SELECT id FROM evaluation_metrics WHERE learner_id = 'user-demo-student'").fetchone()
        if not demo_metric:
            conn.execute(
                """INSERT INTO evaluation_metrics 
                   (learner_id, learning_gain, hint_efficiency, avg_hints_per_problem, task_completion_rate, time_to_completion, satisfaction_score, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("user-demo-student", 0.45, 0.78, 1.2, 0.80, 42.5, 5, now)
            )


# --- USER AUTHENTICATION QUERIES ---

def get_user_by_email(email: str) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(user_id: str, name: str, email: str, password_hash: str, role: str = "student") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    clean_email = email.strip().lower()
    with connection() as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name.strip(), clean_email, password_hash, role, now)
        )
        conn.execute("INSERT OR IGNORE INTO learners VALUES (?, ?)", (user_id, name.strip()))
    return {"id": user_id, "name": name.strip(), "email": clean_email, "role": role, "created_at": now}


# --- CURRICULUM & PROBLEM QUERIES ---

def list_concepts() -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM concepts ORDER BY order_index").fetchall()
    return [dict(r) for r in rows]


def get_concept(concept_id: str) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
    return dict(row) if row else None


def get_problem(problem_id: int) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    return dict(row) if row else None


def list_problems(concept_id: Optional[str] = None) -> list[dict]:
    with connection() as conn:
        if concept_id:
            rows = conn.execute("SELECT * FROM problems WHERE concept_id = ? ORDER BY id", (concept_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM problems ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def create_custom_problem(creator_id: str, title: str, description: str, concept_id: str, difficulty: str, starter_code: str, test_cases: list[dict], expected_behavior: str = "") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    test_cases_json = json.dumps(test_cases)
    with connection() as conn:
        existing = conn.execute(
            "SELECT id FROM custom_questions WHERE creator_id = ? AND title = ?",
            (creator_id, title)
        ).fetchone()
        if existing:
            custom_id = existing["id"]
            conn.execute(
                """UPDATE custom_questions 
                   SET description = ?, concept_id = ?, difficulty = ?, starter_code = ?, test_cases_json = ?, created_at = ?
                   WHERE id = ?""",
                (description, concept_id, difficulty, starter_code, test_cases_json, now, custom_id)
            )
        else:
            cursor = conn.execute(
                """INSERT INTO custom_questions 
                   (creator_id, title, description, concept_id, difficulty, starter_code, test_cases_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (creator_id, title, description, concept_id, difficulty, starter_code, test_cases_json, now)
            )
            custom_id = cursor.lastrowid
        # Map custom question to problem space
        problem_id = 10000 + custom_id
        conn.execute(
            """INSERT INTO problems 
               (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'custom')
               ON CONFLICT(id) DO UPDATE SET
                   title = excluded.title,
                   description = excluded.description,
                   difficulty = excluded.difficulty,
                   topic = excluded.topic,
                   starter_code = excluded.starter_code,
                   expected_behavior = excluded.expected_behavior,
                   concept_id = excluded.concept_id,
                   test_cases_json = excluded.test_cases_json,
                   is_custom = 1,
                   creator_id = excluded.creator_id,
                   source = 'custom'""",
            (problem_id, title, description, difficulty, concept_id, starter_code, expected_behavior or description, concept_id, test_cases_json, creator_id)
        )
    return get_problem(problem_id)


def list_custom_problems(creator_id: Optional[str] = None) -> list[dict]:
    with connection() as conn:
        if creator_id:
            rows = conn.execute("SELECT * FROM problems WHERE is_custom = 1 AND creator_id = ? ORDER BY id DESC", (creator_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM problems WHERE is_custom = 1 ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


# --- LEARNER STATE & CONCEPT PROGRESS QUERIES ---

DEFAULT_STATE = {
    "mastery": 0.35,
    "confidence": 0.50,
    "confusion": 0.20,
    "cognitive_load": 0.30,
    "progress": 0.0,
    "attempts": 0,
    "solved_count": 0,
    "hints_used": 0,
    "response_time": 0.0
}


def get_state(learner_id: str) -> dict:
    with connection() as conn:
        row = conn.execute("SELECT state_json FROM learner_states WHERE learner_id = ?", (learner_id,)).fetchone()
    if row:
        data = json.loads(row["state_json"])
        # Ensure all default keys exist
        for k, v in DEFAULT_STATE.items():
            if k not in data:
                data[k] = v
        return data
    return dict(DEFAULT_STATE)


def get_concept_progress(learner_id: str) -> dict[str, dict]:
    """Retrieve concept-wise progress map for learner."""
    with connection() as conn:
        rows = conn.execute("SELECT * FROM concept_progress WHERE learner_id = ?", (learner_id,)).fetchall()
    res = {}
    for row in rows:
        d = dict(row)
        m = d.get("mastery", 0.35)
        d["progress_pct"] = int(round(m * 100))
        res[d["concept_id"]] = d
    return res


def get_concept_state(learner_id: str, concept_id: str) -> dict:
    """Fetch concept state with default BKT and EWMA priors if missing."""
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM concept_progress WHERE learner_id = ? AND concept_id = ?",
            (learner_id, concept_id)
        ).fetchone()
    if row:
        return dict(row)
    return {
        "learner_id": learner_id,
        "concept_id": concept_id,
        "mastery": 0.20,
        "confidence": 0.50,
        "confusion": 0.00,
        "cognitive_load": 0.00,
        "attempts_count": 0,
        "success_count": 0,
        "hints_used": 0
    }

def get_recent_concept_history(learner_id: str, concept_id: str, limit: int = 5) -> list[dict]:
    """Fetch recent interaction attempts for a specific concept to compute repeat errors and behavioral signals."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM attempts 
               WHERE learner_id = ? AND concept_id = ? 
               ORDER BY id DESC LIMIT ?""",
            (learner_id, concept_id, limit)
        ).fetchall()
    return [dict(row) for row in rows]

def update_concept_progress_db(
    learner_id: str, 
    concept_id: str, 
    mastery: float, 
    confidence: float, 
    confusion: float, 
    cognitive_load: float, 
    passed: bool, 
    hints: int
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM concept_progress WHERE learner_id = ? AND concept_id = ?",
            (learner_id, concept_id)
        ).fetchone()
        if row:
            attempts_count = row["attempts_count"] + 1
            success_count = row["success_count"] + (1 if passed else 0)
            hints_used_total = row.get("hints_used", 0) + hints
            conn.execute(
                """UPDATE concept_progress 
                   SET mastery = ?, confidence = ?, confusion = ?, cognitive_load = ?, 
                       attempts_count = ?, success_count = ?, hints_used = ?, last_attempt_at = ?, status = 'in_progress'
                   WHERE learner_id = ? AND concept_id = ?""",
                (mastery, confidence, confusion, cognitive_load, attempts_count, success_count, hints_used_total, now, learner_id, concept_id)
            )
        else:
            attempts_count = 1
            success_count = 1 if passed else 0
            hints_used_total = hints
            conn.execute(
                """INSERT INTO concept_progress 
                   (learner_id, concept_id, mastery, confidence, confusion, cognitive_load, attempts_count, success_count, hints_used, last_attempt_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_progress')""",
                (learner_id, concept_id, mastery, confidence, confusion, cognitive_load, attempts_count, success_count, hints_used_total, now)
            )
    return {
        "concept_id": concept_id, 
        "mastery": mastery, 
        "confidence": confidence, 
        "confusion": confusion, 
        "cognitive_load": cognitive_load, 
        "attempts_count": attempts_count, 
        "success_count": success_count,
        "hints_used": hints_used_total
    }


def save_attempt_and_state(
    learner_id: str,
    problem_id: int,
    code: str,
    passed: bool,
    error_type: str,
    state: dict,
    concept_id: Optional[str] = None,
    response_time: float = 0.0,
    scaffolding_level: int = 1,
    hints_used: int = 0
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute("INSERT OR IGNORE INTO learners VALUES (?, ?)", (learner_id, learner_id.replace("-", " ").title()))
        conn.execute(
            """INSERT INTO attempts 
               (learner_id, problem_id, code, passed, error_type, created_at, concept_id, response_time, scaffolding_level, hints_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (learner_id, problem_id, code, int(passed), error_type, now, concept_id, response_time, scaffolding_level, hints_used)
        )
        conn.execute(
            """INSERT INTO learner_states VALUES (?, ?, ?)
               ON CONFLICT(learner_id) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at""",
            (learner_id, json.dumps(state), now)
        )
        # S-07 / R-13: Append to state_history for longitudinal analytics
        try:
            conn.execute(
                """INSERT INTO state_history 
                   (learner_id, problem_id, concept_id, mastery, confidence, confusion, cognitive_load, consecutive_fails, scaffolding_level, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    learner_id,
                    problem_id,
                    concept_id,
                    float(state.get("mastery", 0.35)),
                    float(state.get("confidence", 0.50)),
                    float(state.get("confusion", 0.00)),
                    float(state.get("cognitive_load", 0.00)),
                    int(state.get("consecutive_fails", 0)),
                    scaffolding_level,
                    now
                )
            )
        except Exception:
            pass


def history(learner_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """SELECT a.id, a.problem_id, p.title as problem_title, a.passed, a.error_type, 
                      a.created_at, a.concept_id, a.response_time, a.scaffolding_level, a.hints_used, a.code
               FROM attempts a
               LEFT JOIN problems p ON a.problem_id = p.id
               WHERE a.learner_id = ?
               ORDER BY a.id DESC""",
            (learner_id,)
        ).fetchall()
    return [dict(row) for row in rows]


# --- CHAT & HINTS QUERIES ---

def save_chat_message(learner_id: str, role: str, content: str, problem_id: Optional[int] = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_messages (learner_id, problem_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (learner_id, problem_id, role, content, now)
        )
        msg_id = cursor.lastrowid
    return {"id": msg_id, "learner_id": learner_id, "problem_id": problem_id, "role": role, "content": content, "created_at": now}


def get_chat_history(learner_id: str, limit: int = 50) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, learner_id, problem_id, role, content, created_at FROM chat_messages WHERE learner_id = ? ORDER BY id ASC LIMIT ?",
            (learner_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def save_hint(learner_id: str, problem_id: int, level: int, hint_text: str, focus: str = "Conceptual") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute(
            "INSERT INTO hints (learner_id, problem_id, level, hint_text, created_at, focus) VALUES (?, ?, ?, ?, ?, ?)",
            (learner_id, problem_id, level, hint_text, now, focus)
        )


def get_problem_hints(learner_id: str, problem_id: int) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM hints WHERE learner_id = ? AND problem_id = ? ORDER BY id ASC",
            (learner_id, problem_id)
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_problem_attempts(learner_id: str, problem_id: int, limit: int = 10) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM attempts WHERE learner_id = ? AND problem_id = ? ORDER BY id DESC LIMIT ?",
            (learner_id, problem_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# --- SESSION TRACKING QUERIES ---

def get_session_by_id(session_id: int) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM learning_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("started_at"):
        try:
            start_dt = datetime.fromisoformat(d["started_at"])
            end_dt = datetime.fromisoformat(d["ended_at"]) if d.get("ended_at") else datetime.now(timezone.utc)
            d["duration_seconds"] = max(0, int((end_dt - start_dt).total_seconds()))
        except Exception:
            d["duration_seconds"] = 0
    else:
        d["duration_seconds"] = 0
    d["status"] = "completed" if d.get("ended_at") else "active"
    return d


def start_learning_session(learner_id: str) -> dict:
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    with connection() as conn:
        # Check for active (unended) session for this learner
        active_row = conn.execute(
            "SELECT * FROM learning_sessions WHERE learner_id = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1",
            (learner_id,)
        ).fetchone()
        if active_row:
            active_sess = dict(active_row)
            try:
                started_dt = datetime.fromisoformat(active_sess["started_at"])
                age = (now_dt - started_dt).total_seconds()
            except Exception:
                age = 0
            if age < 7200:  # Within 2 hours, reuse idempotently
                active_sess["duration_seconds"] = int(age)
                active_sess["status"] = "active"
                return active_sess
            else:
                # Reconcile stale session (> 2 hours old)
                reconciled_end = (started_dt + timedelta(minutes=45)).isoformat()
                conn.execute(
                    "UPDATE learning_sessions SET ended_at = ? WHERE id = ?",
                    (reconciled_end, active_sess["id"])
                )

        cursor = conn.execute(
            "INSERT INTO learning_sessions (learner_id, started_at, problems_attempted, problems_solved) VALUES (?, ?, 0, 0)",
            (learner_id, now)
        )
        sess_id = cursor.lastrowid
    return {
        "id": sess_id,
        "learner_id": learner_id,
        "started_at": now,
        "ended_at": None,
        "duration_seconds": 0,
        "status": "active",
        "problems_attempted": 0,
        "problems_solved": 0
    }


def update_learning_session(session_id: int, attempted: bool = True, solved: bool = False) -> None:
    with connection() as conn:
        conn.execute(
            """UPDATE learning_sessions 
               SET problems_attempted = problems_attempted + ?,
                   problems_solved = problems_solved + ?
               WHERE id = ?""",
            (1 if attempted else 0, 1 if solved else 0, session_id)
        )


def end_learning_session(session_id: int) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute("UPDATE learning_sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL", (now, session_id))
    return get_session_by_id(session_id)


def get_learning_sessions(learner_id: str, limit: int = 10) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM learning_sessions WHERE learner_id = ? ORDER BY id DESC LIMIT ?",
            (learner_id, limit)
        ).fetchall()
    now_dt = datetime.now(timezone.utc)
    sessions = []
    for r in rows:
        d = dict(r)
        if d.get("started_at"):
            try:
                start_dt = datetime.fromisoformat(d["started_at"])
                end_dt = datetime.fromisoformat(d["ended_at"]) if d.get("ended_at") else now_dt
                d["duration_seconds"] = max(0, int((end_dt - start_dt).total_seconds()))
            except Exception:
                d["duration_seconds"] = 0
        else:
            d["duration_seconds"] = 0
        d["status"] = "completed" if d.get("ended_at") else "active"
        sessions.append(d)
    return sessions


# --- RECOMMENDATIONS PERSISTENCE ---

def save_recommendation(learner_id: str, problem_id: Optional[int], concept_id: Optional[str], reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute(
            "INSERT INTO recommendations (learner_id, problem_id, concept_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (learner_id, problem_id, concept_id, reason, now)
        )


def get_latest_recommendation(learner_id: str) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE learner_id = ? ORDER BY id DESC LIMIT 1",
            (learner_id,)
        ).fetchone()
    return dict(row) if row else None


# --- EVALUATION METRICS QUERIES ---

def save_evaluation_metric(
    learner_id: str,
    learning_gain: float,
    hint_efficiency: float,
    avg_hints_per_problem: float,
    task_completion_rate: float,
    time_to_completion: float,
    satisfaction_score: Optional[int] = None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute(
            """INSERT INTO evaluation_metrics 
               (learner_id, learning_gain, hint_efficiency, avg_hints_per_problem, task_completion_rate, time_to_completion, satisfaction_score, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (learner_id, learning_gain, hint_efficiency, avg_hints_per_problem, task_completion_rate, time_to_completion, satisfaction_score, now)
        )


def get_latest_metrics(learner_id: str) -> Optional[dict]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM evaluation_metrics WHERE learner_id = ? ORDER BY id DESC LIMIT 1",
            (learner_id,)
        ).fetchone()
    return dict(row) if row else None


def get_all_student_metrics() -> list[dict]:
    with connection() as conn:
        users = conn.execute("SELECT id, name, email FROM users WHERE role = 'student' OR role IS NULL").fetchall()
        
        results = []
        for u in users:
            uid = u["id"]
            row = conn.execute(
                "SELECT * FROM evaluation_metrics WHERE learner_id = ? ORDER BY id DESC LIMIT 1",
                (uid,)
            ).fetchone()
            
            # Get basic BKT mastery from state
            state_row = conn.execute("SELECT state_json FROM learner_states WHERE learner_id = ?", (uid,)).fetchone()
            mastery = 0.35
            progress = 0.0
            if state_row:
                try:
                    state_data = json.loads(state_row["state_json"])
                    mastery = state_data.get("mastery", 0.35)
                    progress = state_data.get("progress", 0.0)
                except Exception:
                    pass
            
            # Format combined metrics
            metrics = dict(row) if row else {
                "learning_gain": 0.0,
                "hint_efficiency": 0.0,
                "avg_hints_per_problem": 0.0,
                "task_completion_rate": 0.0,
                "time_to_completion": 0.0,
                "satisfaction_score": None
            }
            
            results.append({
                "id": uid,
                "name": u["name"],
                "email": u["email"],
                "mastery": mastery,
                "progress": progress,
                "metrics": metrics
            })
    return results


# --- S-07, R-03, R-13, R-18, R-25 ENHANCEMENT HELPERS ---

def get_state_history(learner_id: str, limit: int = 50) -> list[dict]:
    """Fetch longitudinal cognitive state progression records for a learner (R-13)."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM state_history 
               WHERE learner_id = ? 
               ORDER BY id ASC LIMIT ?""",
            (learner_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def record_learner_misconception(learner_id: str, concept_id: str, misconception_code: str, error_type: str = "") -> None:
    """Record or increment recurring misconceptions for longitudinal tracking (R-03)."""
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        existing = conn.execute(
            """SELECT id, occurrence_count FROM learner_misconceptions 
               WHERE learner_id = ? AND concept_id = ? AND misconception_code = ?""",
            (learner_id, concept_id, misconception_code)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE learner_misconceptions 
                   SET occurrence_count = occurrence_count + 1, last_seen = ? 
                   WHERE id = ?""",
                (now, existing["id"])
            )
        else:
            conn.execute(
                """INSERT INTO learner_misconceptions 
                   (learner_id, concept_id, misconception_code, error_type, occurrence_count, last_seen, resolved)
                   VALUES (?, ?, ?, ?, 1, ?, 0)""",
                (learner_id, concept_id, misconception_code, error_type, now)
            )


def get_learner_misconceptions(learner_id: str) -> list[dict]:
    """Retrieve recurring misconception profiles for a learner (R-03)."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM learner_misconceptions 
               WHERE learner_id = ? 
               ORDER BY occurrence_count DESC, id DESC""",
            (learner_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def save_reflection_response(
    learner_id: str,
    problem_id: int,
    prompt_text: str,
    response_text: str,
    session_id: Optional[int] = None,
    quality_score: float = 1.0
) -> dict:
    """Persist student metacognitive reflection answer (R-25)."""
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO reflection_responses 
               (session_id, learner_id, problem_id, prompt_text, response_text, quality_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, learner_id, problem_id, prompt_text, response_text, quality_score, now)
        )
        resp_id = cursor.lastrowid
    return {
        "id": resp_id,
        "learner_id": learner_id,
        "problem_id": problem_id,
        "response_text": response_text,
        "quality_score": quality_score,
        "created_at": now
    }


def get_reflection_responses(learner_id: str, limit: int = 20) -> list[dict]:
    """Fetch stored reflection responses for a learner (R-25)."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM reflection_responses 
               WHERE learner_id = ? 
               ORDER BY id DESC LIMIT ?""",
            (learner_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def save_satisfaction_survey(
    learner_id: str,
    session_id: Optional[int],
    usefulness_score: int,
    clarity_score: int,
    hint_adequacy_score: int,
    perceived_adaptivity_score: int,
    comments: str = ""
) -> dict:
    """Record multi-item Likert satisfaction evaluation (R-18)."""
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO satisfaction_surveys 
               (learner_id, session_id, usefulness_score, clarity_score, hint_adequacy_score, perceived_adaptivity_score, comments, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (learner_id, session_id, usefulness_score, clarity_score, hint_adequacy_score, perceived_adaptivity_score, comments, now)
        )
        survey_id = cursor.lastrowid
    return {
        "id": survey_id,
        "learner_id": learner_id,
        "usefulness_score": usefulness_score,
        "clarity_score": clarity_score,
        "hint_adequacy_score": hint_adequacy_score,
        "perceived_adaptivity_score": perceived_adaptivity_score,
        "comments": comments,
        "recorded_at": now
    }


def get_weakest_concepts(learner_id: str, limit: int = 5) -> list[dict]:
    """Identify weak topics where student has lowest mastery or highest confusion (R-13)."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT cp.concept_id, c.title as concept_title, cp.mastery, cp.confusion, cp.attempts_count, cp.success_count
               FROM concept_progress cp
               JOIN concepts c ON cp.concept_id = c.id
               WHERE cp.learner_id = ? AND cp.attempts_count > 0
               ORDER BY cp.mastery ASC, cp.confusion DESC
               LIMIT ?""",
            (learner_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_student_drilldown(student_id: str) -> Optional[dict]:
    """R-14: Comprehensive teacher analytics drilldown for a single student."""
    with connection() as conn:
        user_row = conn.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?", (student_id,)).fetchone()
        if not user_row:
            return None
        student_info = dict(user_row)

        # Concept progress
        c_rows = conn.execute(
            """SELECT cp.*, c.title as concept_title, c.category 
               FROM concept_progress cp 
               JOIN concepts c ON cp.concept_id = c.id 
               WHERE cp.learner_id = ? 
               ORDER BY c.order_index ASC""",
            (student_id,)
        ).fetchall()
        concept_breakdown = [dict(r) for r in c_rows]

        # Recent attempts
        att_rows = conn.execute(
            """SELECT a.*, p.title as problem_title 
               FROM attempts a 
               LEFT JOIN problems p ON a.problem_id = p.id 
               WHERE a.learner_id = ? 
               ORDER BY a.id DESC LIMIT 20""",
            (student_id,)
        ).fetchall()
        recent_attempts = [dict(r) for r in att_rows]

        # State history
        sh_rows = conn.execute(
            "SELECT * FROM state_history WHERE learner_id = ? ORDER BY id ASC LIMIT 50",
            (student_id,)
        ).fetchall()
        state_progression = [dict(r) for r in sh_rows]

        # Misconceptions
        m_rows = conn.execute(
            "SELECT * FROM learner_misconceptions WHERE learner_id = ? ORDER BY occurrence_count DESC",
            (student_id,)
        ).fetchall()
        misconceptions = [dict(r) for r in m_rows]

        # At-risk alert indicator: flagged if average confusion >= 0.50 or consecutive fails >= 3
        latest_sh = state_progression[-1] if state_progression else {}
        is_at_risk = (
            latest_sh.get("confusion", 0) >= 0.50 or
            latest_sh.get("consecutive_fails", 0) >= 3 or
            (latest_sh.get("cognitive_load", 0) >= 0.65 and latest_sh.get("mastery", 0) < 0.35)
        )

        return {
            "student": student_info,
            "concept_breakdown": concept_breakdown,
            "recent_attempts": recent_attempts,
            "state_progression": state_progression,
            "misconceptions": misconceptions,
            "is_at_risk": bool(is_at_risk),
            "at_risk_reason": "High persistent confusion or cognitive load" if is_at_risk else "Normal progression"
        }

