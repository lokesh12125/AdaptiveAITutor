"""Authoritative SQLite database layer for structured tutoring platform data."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DATABASE_PATH
from .curriculum import CURRICULUM_CONCEPTS
from .codenet import get_codenet_subset

INITIAL_PROBLEMS = [
    (1, "Sum of an Array", "Write sum_array(numbers) that returns the sum of all numbers.", "easy", "lists", "def sum_array(numbers):\n    # write your code here\n    pass", "sum_array([2, 3, 5]) returns 10", "lists", json.dumps([{"input": [[2, 3, 5]], "expected": 10}, {"input": [[]], "expected": 0}]), 0, None, "builtin"),
    (2, "Maximum Element", "Write find_max(numbers) that returns the largest number in a non-empty list.", "easy", "lists", "def find_max(numbers):\n    # write your code here\n    pass", "find_max([4, 1, 9]) returns 9", "lists", json.dumps([{"input": [[4, 1, 9]], "expected": 9}, {"input": [[-5, -2, -8]], "expected": -2}]), 0, None, "builtin"),
    (3, "Count Vowels", "Write count_vowels(text) that counts a, e, i, o, and u regardless of case.", "easy", "strings", "def count_vowels(text):\n    # write your code here\n    pass", "count_vowels('Education') returns 5", "strings", json.dumps([{"input": ["Education"], "expected": 5}, {"input": ["sky"], "expected": 0}]), 0, None, "builtin"),
    (4, "Check Palindrome", "Write is_palindrome(text) that ignores case and spaces.", "medium", "strings", "def is_palindrome(text):\n    # write your code here\n    pass", "is_palindrome('Never odd or even') returns True", "strings", json.dumps([{"input": ["Never odd or even"], "expected": True}, {"input": ["Python"], "expected": False}]), 0, None, "builtin"),
    (5, "Two Sum", "Write two_sum(numbers, target) returning indices of two values that add to target.", "medium", "arrays", "def two_sum(numbers, target):\n    # write your code here\n    pass", "two_sum([2, 7, 11, 15], 9) returns [0, 1]", "hash-map-problems", json.dumps([{"input": [[2, 7, 11, 15], 9], "expected": [0, 1]}]), 0, None, "builtin"),
]


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_add_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    col_name = column_def.strip().split()[0]
    cursor = conn.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in cursor.fetchall()]
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def initialize_database() -> None:
    with connection() as conn:
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

        # Seed initial built-in problems if missing
        conn.executemany("""
            INSERT OR IGNORE INTO problems 
            (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, INITIAL_PROBLEMS)

        # Seed 49 curriculum concepts and associated problems
        for concept in CURRICULUM_CONCEPTS:
            conn.execute("""
                INSERT OR REPLACE INTO concepts 
                (id, title, category, difficulty, description, learning_objectives, explanation, examples_json, prerequisites_json, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    INSERT OR IGNORE INTO problems
                    (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 'curriculum')
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

        # Seed IBM Project CodeNet subset problems
        for cp in get_codenet_subset():
            conn.execute("""
                INSERT OR IGNORE INTO problems
                (id, title, description, difficulty, topic, starter_code, expected_behavior, concept_id, test_cases_json, is_custom, creator_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
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

        # Seed default historical learners with consistent 8D vectors
        default_demos = [
            ("synthetic-1", [0.25, 0.30, 0.75, 0.70, 0.15, 0.80, 0.70, 0.40], "Break down syntax rules, isolate the offending line, and check matching delimiters."),
            ("synthetic-2", [0.55, 0.50, 0.45, 0.40, 0.50, 0.40, 0.35, 0.30], "Provide pseudocode structure and prompt tracing on small sample inputs."),
            ("synthetic-3", [0.85, 0.80, 0.15, 0.20, 0.85, 0.10, 0.10, 0.20], "Challenge with edge cases and prompt explanation of algorithmic time complexity.")
        ]
        conn.executemany("INSERT OR REPLACE INTO historical_learners VALUES (?, ?, ?)", [(k, json.dumps(v), inter) for k, v, inter in default_demos])


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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'custom')""",
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
    return {row["concept_id"]: dict(row) for row in rows}


def update_concept_progress_db(learner_id: str, concept_id: str, mastery: float, passed: bool) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM concept_progress WHERE learner_id = ? AND concept_id = ?",
            (learner_id, concept_id)
        ).fetchone()
        if row:
            attempts_count = row["attempts_count"] + 1
            success_count = row["success_count"] + (1 if passed else 0)
            conn.execute(
                """UPDATE concept_progress 
                   SET mastery = ?, attempts_count = ?, success_count = ?, last_attempt_at = ?, status = 'in_progress'
                   WHERE learner_id = ? AND concept_id = ?""",
                (mastery, attempts_count, success_count, now, learner_id, concept_id)
            )
        else:
            attempts_count = 1
            success_count = 1 if passed else 0
            conn.execute(
                """INSERT INTO concept_progress 
                   (learner_id, concept_id, mastery, attempts_count, success_count, last_attempt_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'in_progress')""",
                (learner_id, concept_id, mastery, attempts_count, success_count, now)
            )
    return {"concept_id": concept_id, "mastery": mastery, "attempts_count": attempts_count, "success_count": success_count}


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


def save_hint(learner_id: str, problem_id: int, level: int, hint_text: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute(
            "INSERT INTO hints (learner_id, problem_id, level, hint_text, created_at) VALUES (?, ?, ?, ?, ?)",
            (learner_id, problem_id, level, hint_text, now)
        )


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
