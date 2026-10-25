"""Comprehensive automated tests for curriculum content integrity and session lifecycle management."""
import json
import sqlite3
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.curriculum import CURRICULUM_CONCEPTS
from app.codenet import get_codenet_subset
from app.database import (
    INITIAL_PROBLEMS,
    connection,
    start_learning_session,
    end_learning_session,
    get_session_by_id,
    get_learning_sessions
)
from app.services.code_runner import evaluate
from app.auth import create_access_token


class CurriculumAndSessionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def auth_headers(self, user_id: str, role: str = "student") -> dict:
        token = create_access_token(user_id=user_id, name="Test User", email=f"{user_id}@adaptive.edu", role=role)
        return {"Authorization": f"Bearer {token}"}

    # --- TASK A & C: CURRICULUM INTEGRITY & CONTENT VALIDATION ---

    def test_01_curriculum_concept_taxonomy(self):
        """Verify the 49 distinct concepts remain intact with valid categories and metadata."""
        self.assertEqual(len(CURRICULUM_CONCEPTS), 49)
        categories = {c["category"] for c in CURRICULUM_CONCEPTS}
        self.assertIn("Foundations", categories)
        self.assertIn("Collections", categories)
        self.assertIn("Intermediate Python", categories)
        self.assertIn("Problem Solving", categories)

        for concept in CURRICULUM_CONCEPTS:
            self.assertTrue(bool(concept.get("id")))
            self.assertTrue(bool(concept.get("title")))
            self.assertTrue(bool(concept.get("description")))
            self.assertTrue(bool(concept.get("explanation")))
            self.assertGreater(len(concept.get("problems", [])), 0)

    def test_02_no_duplicate_or_missing_problem_ids(self):
        """Verify all problem IDs are positive integers and unique across curriculum, codenet, and initial."""
        seen_ids = set()
        
        # Initial problems
        for p in INITIAL_PROBLEMS:
            pid = p[0]
            self.assertNotIn(pid, seen_ids, f"Duplicate problem ID {pid} in INITIAL_PROBLEMS")
            seen_ids.add(pid)
            
        # Curriculum problems
        for c in CURRICULUM_CONCEPTS:
            for p in c["problems"]:
                pid = p["id"]
                self.assertNotIn(pid, seen_ids, f"Duplicate problem ID {pid} in concept {c['id']}")
                seen_ids.add(pid)
                
        # CodeNet problems
        for cp in get_codenet_subset():
            pid = cp["id"]
            self.assertNotIn(pid, seen_ids, f"Duplicate problem ID {pid} in CodeNet")
            seen_ids.add(pid)

        # Expected counts
        self.assertEqual(len(seen_ids), 5 + 51 + 7)  # 5 initial, 51 curriculum (49 + 2 trees), 7 codenet = 63

    def test_03_no_placeholder_content_and_rich_descriptions(self):
        """Verify all problems contain structured Markdown sections and zero placeholder phrases."""
        forbidden_phrases = ["todo", "placeholder", "write code here without tests", "tbd"]

        with connection() as conn:
            problems = conn.execute("SELECT id, title, description, starter_code, test_cases_json FROM problems WHERE is_custom = 0").fetchall()

        self.assertGreaterEqual(len(problems), 63)

        for p in problems:
            pid = p["id"]
            title = p["title"]
            desc = p["description"]
            starter = p["starter_code"]
            tcs = json.loads(p["test_cases_json"])

            for phrase in forbidden_phrases:
                self.assertNotIn(phrase, desc.lower(), f"Problem {pid} ({title}) contains placeholder phrase '{phrase}'")

            # Check markdown structure
            self.assertIn("### Problem Statement", desc, f"Problem {pid} ({title}) missing Problem Statement heading")
            self.assertIn("### Examples", desc, f"Problem {pid} ({title}) missing Examples heading")

            # Check starter code exists
            self.assertTrue(bool(starter.strip()), f"Problem {pid} ({title}) missing starter code")

            # Check meaningful test cases
            self.assertGreaterEqual(len(tcs), 1, f"Problem {pid} ({title}) has no test cases")
            for tc in tcs:
                self.assertTrue("input" in tc or "test_script" in tc, f"Problem {pid} test case missing input or script")

    def test_04_trees_curriculum_coverage(self):
        """Verify Binary Tree problems (150 and 151) test depth and inversion on binary trees."""
        with connection() as conn:
            p150 = conn.execute("SELECT * FROM problems WHERE id = 150").fetchone()
            p151 = conn.execute("SELECT * FROM problems WHERE id = 151").fetchone()

        self.assertIsNotNone(p150, "Problem 150 (Binary Tree Maximum Depth) missing from database")
        self.assertIsNotNone(p151, "Problem 151 (Invert Binary Tree) missing from database")

        self.assertEqual(p150["title"], "Binary Tree Maximum Depth")
        self.assertEqual(p151["title"], "Invert Binary Tree")

        # Verify correct solution for 150 passes and buggy fails
        sol_150 = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def max_depth(root):
    if not root: return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
"""
        res_pass = evaluate(sol_150, 150)
        self.assertTrue(res_pass["passed"], f"Problem 150 correct solution failed: {res_pass}")

        buggy_150 = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def max_depth(root):
    if not root: return 0
    return max(max_depth(root.left), max_depth(root.right))  # Bug: missing + 1
"""
        res_fail = evaluate(buggy_150, 150)
        self.assertFalse(res_fail["passed"], "Problem 150 buggy solution should have failed")

        # Verify correct solution for 151 passes
        sol_151 = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def invert_tree(root):
    if not root: return None
    root.left, root.right = invert_tree(root.right), invert_tree(root.left)
    return root
"""
        res_pass_151 = evaluate(sol_151, 151)
        self.assertTrue(res_pass_151["passed"], f"Problem 151 correct solution failed: {res_pass_151}")

    def test_05_curriculum_test_cases_distinguish_incorrect_implementations(self):
        """Verify test cases detect common logic defects across multiple curriculum pillars."""
        # 1. Stack (Problem 145: Valid Parentheses)
        # Buggy implementation only checks counts, ignoring order (e.g., '([)]')
        buggy_stack = """def is_valid_parentheses(s):
    return s.count('(') == s.count(')') and s.count('[') == s.count(']') and s.count('{') == s.count('}')
"""
        res_stack = evaluate(buggy_stack, 145)
        self.assertFalse(res_stack["passed"], "Problem 145 should fail count-only bracket checker")

        # 2. Two-Pointer (Problem 148: Two-Pointer Palindrome)
        # Buggy implementation only checks first and last character
        buggy_pal = """def is_palindrome_fast(s):
    if len(s) <= 1: return True
    return s[0] == s[-1]
"""
        res_pal = evaluate(buggy_pal, 148)
        self.assertFalse(res_pal["passed"], "Problem 148 should fail first-and-last-only palindrome checker")

        # 3. Hash Map (Problem 144: Two Sum Fast)
        # Buggy returns numbers instead of indices
        buggy_map = """def two_sum_fast(numbers, target):
    seen = set()
    for num in numbers:
        comp = target - num
        if comp in seen: return [comp, num]
        seen.add(num)
    return None
"""
        res_map = evaluate(buggy_map, 144)
        self.assertFalse(res_map["passed"], "Problem 144 should fail returning values instead of indices")

    # --- TASK B & C: SESSION LIFECYCLE, IDEMPOTENCY & AUTHORIZATION ---

    def test_06_session_start_and_end_lifecycle(self):
        """Test standard session lifecycle through API endpoints."""
        learner_id = f"sess-test-{uuid.uuid4().hex[:6]}"
        headers = self.auth_headers(learner_id)

        # 1. Start session
        start_res = self.client.post("/api/sessions/start", headers=headers, json={"learner_id": learner_id})
        self.assertEqual(start_res.status_code, 200)
        s_data = start_res.json()
        self.assertEqual(s_data["learner_id"], learner_id)
        self.assertEqual(s_data["status"], "active")
        self.assertIsNone(s_data["ended_at"])
        session_id = s_data["id"]

        # 2. End session explicitly
        end_res = self.client.post(f"/api/sessions/{session_id}/end", headers=headers)
        self.assertEqual(end_res.status_code, 200)
        end_data = end_res.json()
        self.assertEqual(end_data["status"], "ok")
        self.assertEqual(end_data["session"]["status"], "completed")
        self.assertIsNotNone(end_data["session"]["ended_at"])
        self.assertGreaterEqual(end_data["session"]["duration_seconds"], 0)

    def test_07_duplicate_session_prevention_idempotency(self):
        """Calling /api/sessions/start multiple times within active window returns existing session without creating duplicates."""
        learner_id = f"idemp-test-{uuid.uuid4().hex[:6]}"
        headers = self.auth_headers(learner_id)

        # Call start 3 times rapidly
        res1 = self.client.post("/api/sessions/start", headers=headers, json={"learner_id": learner_id}).json()
        res2 = self.client.post("/api/sessions/start", headers=headers, json={"learner_id": learner_id}).json()
        res3 = self.client.post("/api/sessions/start", headers=headers, json={"learner_id": learner_id}).json()

        self.assertEqual(res1["id"], res2["id"])
        self.assertEqual(res2["id"], res3["id"])

        # Check database records
        sessions = get_learning_sessions(learner_id)
        self.assertEqual(len(sessions), 1)

    def test_08_stale_session_reconciliation_policy(self):
        """Unended sessions older than 2 hours are reconciled and closed before starting a fresh session."""
        learner_id = f"stale-reconcile-{uuid.uuid4().hex[:6]}"
        stale_start = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()

        # Insert a stale unended session directly in DB
        with connection() as conn:
            cursor = conn.execute(
                "INSERT INTO learning_sessions (learner_id, started_at, problems_attempted, problems_solved) VALUES (?, ?, 2, 1)",
                (learner_id, stale_start)
            )
            old_sess_id = cursor.lastrowid

        headers = self.auth_headers(learner_id)
        start_res = self.client.post("/api/sessions/start", headers=headers, json={"learner_id": learner_id})
        self.assertEqual(start_res.status_code, 200)
        new_sess = start_res.json()

        # A brand new session is created
        self.assertNotEqual(new_sess["id"], old_sess_id)
        self.assertEqual(new_sess["status"], "active")

        # The old stale session is reconciled with completed status and ended_at
        old_sess = get_session_by_id(old_sess_id)
        self.assertIsNotNone(old_sess["ended_at"])
        self.assertEqual(old_sess["status"], "completed")

    def test_09_cross_student_session_authorization_forbidden_403(self):
        """Learner A cannot end Learner B's session."""
        student_a = f"student-sess-a-{uuid.uuid4().hex[:6]}"
        student_b = f"student-sess-b-{uuid.uuid4().hex[:6]}"

        headers_a = self.auth_headers(student_a, role="student")
        headers_b = self.auth_headers(student_b, role="student")

        # Student B starts a session
        sess_b = self.client.post("/api/sessions/start", headers=headers_b, json={"learner_id": student_b}).json()
        sess_id = sess_b["id"]

        # Student A attempts to end Student B's session -> 403 Forbidden
        tamper_res = self.client.post(f"/api/sessions/{sess_id}/end", headers=headers_a)
        self.assertEqual(tamper_res.status_code, 403)
        self.assertIn("cannot end another learner", tamper_res.json()["detail"])

        # Student B ends their own session -> 200 OK
        ok_res = self.client.post(f"/api/sessions/{sess_id}/end", headers=headers_b)
        self.assertEqual(ok_res.status_code, 200)

    def test_10_teacher_session_administration_allowed_200(self):
        """Teacher can end any student's session."""
        student_id = f"student-admin-{uuid.uuid4().hex[:6]}"
        teacher_id = f"teacher-admin-{uuid.uuid4().hex[:6]}"

        s_headers = self.auth_headers(student_id, role="student")
        t_headers = self.auth_headers(teacher_id, role="teacher")

        sess = self.client.post("/api/sessions/start", headers=s_headers, json={"learner_id": student_id}).json()
        sess_id = sess["id"]

        # Teacher ends student session -> 200 OK
        t_res = self.client.post(f"/api/sessions/{sess_id}/end", headers=t_headers)
        self.assertEqual(t_res.status_code, 200)
        self.assertEqual(t_res.json()["session"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
