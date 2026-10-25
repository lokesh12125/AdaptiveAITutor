"""Comprehensive test suite covering authentication, 6-agent LangGraph workflow, BKT mastery, custom questions, CodeNet, and evaluation metrics."""
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import llm


class ComprehensiveTutorApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force demo mode during tests so tests are 100% deterministic and do not depend on internet/OpenAI quota
        cls.orig_client = llm._client
        cls.orig_mode = llm.mode
        llm._client = None
        llm.mode = "demo"

    @classmethod
    def tearDownClass(cls):
        llm._client = cls.orig_client
        llm.mode = cls.orig_mode

    def test_01_health_check(self):
        with TestClient(app) as client:
            res = client.get("/api/health")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["backend"], "ok")
            self.assertEqual(data["database"], "ok")
            self.assertEqual(data["chromadb"], "ok")
            self.assertEqual(data["llm"], "demo")

    def test_02_auth_register_and_login(self):
        with TestClient(app) as client:
            email = "student_test@adaptive.edu"
            # 1. Register
            reg_res = client.post("/api/auth/register", json={
                "name": "Alex Student",
                "email": email,
                "password": "secretPassword123"
            })
            # May be 200 or 400 if already registered from a previous test run
            if reg_res.status_code == 200:
                self.assertIn("token", reg_res.json())
                self.assertEqual(reg_res.json()["user"]["name"], "Alex Student")

            # 2. Login
            login_res = client.post("/api/auth/login", json={
                "email": email,
                "password": "secretPassword123"
            })
            self.assertEqual(login_res.status_code, 200)
            token = login_res.json()["token"]
            self.assertTrue(bool(token))

            # 3. Auth Me
            me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(me_res.status_code, 200)
            self.assertEqual(me_res.json()["email"], email)

    def test_02b_seeded_demo_accounts(self):
        with TestClient(app) as client:
            # 1. Student demo login
            student_res = client.post("/api/auth/login", json={
                "email": "demo@student.edu",
                "password": "demo123"
            })
            self.assertEqual(student_res.status_code, 200)
            s_data = student_res.json()
            self.assertEqual(s_data["user"]["role"], "student")
            self.assertTrue(bool(s_data["token"]))

            # 2. Teacher demo login
            teacher_res = client.post("/api/auth/login", json={
                "email": "teacher@adaptive.edu",
                "password": "teacher123"
            })
            self.assertEqual(teacher_res.status_code, 200)
            t_data = teacher_res.json()
            self.assertEqual(t_data["user"]["role"], "teacher")
            self.assertTrue(bool(t_data["token"]))

            # 3. Invalid credentials
            bad_res = client.post("/api/auth/login", json={
                "email": "demo@student.edu",
                "password": "wrongpassword"
            })
            self.assertEqual(bad_res.status_code, 401)

    def test_02c_auth_registration_contract(self):
        with TestClient(app) as client:
            import uuid
            uid_suffix = uuid.uuid4().hex[:6]

            # 1. Registration with 'full_name' (UI contract)
            ui_email = f"ui_test_{uid_suffix}@adaptive.edu"
            ui_res = client.post("/api/auth/register", json={
                "full_name": "UI Tester",
                "email": ui_email,
                "password": "securePassword1"
            })
            self.assertEqual(ui_res.status_code, 200)
            self.assertEqual(ui_res.json()["user"]["name"], "UI Tester")

            # 2. Registration with standard 'name'
            api_email = f"api_test_{uid_suffix}@adaptive.edu"
            api_res = client.post("/api/auth/register", json={
                "name": "API Tester",
                "email": api_email,
                "password": "securePassword2"
            })
            self.assertEqual(api_res.status_code, 200)
            self.assertEqual(api_res.json()["user"]["name"], "API Tester")

            # 3. Duplicate email fails with 400
            dup_res = client.post("/api/auth/register", json={
                "name": "Duplicate Tester",
                "email": api_email,
                "password": "securePassword3"
            })
            self.assertEqual(dup_res.status_code, 400)

            # 4. Password too short (< 4 chars) fails with 422
            short_res = client.post("/api/auth/register", json={
                "name": "Short Pwd",
                "email": f"short_{uid_suffix}@adaptive.edu",
                "password": "abc"
            })
            self.assertEqual(short_res.status_code, 422)

    def test_02d_role_based_access_control(self):
        with TestClient(app) as client:
            # Login as student
            s_res = client.post("/api/auth/login", json={
                "email": "demo@student.edu",
                "password": "demo123"
            })
            s_token = s_res.json()["token"]
            s_id = s_res.json()["user"]["id"]

            # Login as teacher
            t_res = client.post("/api/auth/login", json={
                "email": "teacher@adaptive.edu",
                "password": "teacher123"
            })
            t_token = t_res.json()["token"]

            # 1. Student attempting teacher endpoint gets 403 Forbidden
            forbidden_res = client.get("/api/admin/students", headers={"Authorization": f"Bearer {s_token}"})
            self.assertEqual(forbidden_res.status_code, 403)

            # 2. Teacher accessing teacher endpoint gets 200 OK
            allowed_res = client.get("/api/admin/students", headers={"Authorization": f"Bearer {t_token}"})
            self.assertEqual(allowed_res.status_code, 200)
            students = allowed_res.json()
            self.assertIsInstance(students, list)

            # 3. Student accessing their own state gets 200 OK
            own_state_res = client.get(f"/api/learner/{s_id}", headers={"Authorization": f"Bearer {s_token}"})
            self.assertEqual(own_state_res.status_code, 200)

            # 4. Student accessing another student's state gets 403 Forbidden
            other_state_res = client.get("/api/learner/other-student-id", headers={"Authorization": f"Bearer {s_token}"})
            self.assertEqual(other_state_res.status_code, 403)

            # 5. Teacher accessing student's state gets 200 OK
            teacher_inspect_res = client.get(f"/api/learner/{s_id}", headers={"Authorization": f"Bearer {t_token}"})
            self.assertEqual(teacher_inspect_res.status_code, 200)

    def test_03_curriculum_and_problems(self):
        with TestClient(app) as client:
            # Check 49 concepts
            c_res = client.get("/api/concepts")
            self.assertEqual(c_res.status_code, 200)
            concepts = c_res.json()
            self.assertEqual(len(concepts), 49)

            # Check problems
            p_res = client.get("/api/problems")
            self.assertEqual(p_res.status_code, 200)
            problems = p_res.json()
            self.assertGreaterEqual(len(problems), 50)

            # Check concept detail
            detail_res = client.get("/api/concepts/variables")
            self.assertEqual(detail_res.status_code, 200)
            self.assertIn("concept", detail_res.json())
            self.assertIn("problems", detail_res.json())

    def test_04_code_execution_security(self):
        with TestClient(app) as client:
            # Hostile code attempting to import os
            res = client.post("/api/submit", json={
                "learner_id": "security-tester",
                "problem_id": 1,
                "code": "import os\ndef sum_array(numbers):\n    return 0",
                "response_time": 10.0
            })
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertFalse(body["execution"]["passed"])
            self.assertEqual(body["execution"]["error_type"], "security")

    def test_05_six_agent_workflow_and_bkt_updates(self):
        with TestClient(app) as client:
            learner_id = "test-workflow-student"
            # First attempt: Incorrect submission
            sub1 = client.post("/api/submit", json={
                "learner_id": learner_id,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return 999",
                "response_time": 15.0
            })
            self.assertEqual(sub1.status_code, 200)
            body1 = sub1.json()
            self.assertFalse(body1["execution"]["passed"])
            self.assertIn("Diagnostic Agent", body1["agent_activity"])
            self.assertIn("Learner State Agent", body1["agent_activity"])
            self.assertIn("Similar Learner Retrieval Agent", body1["agent_activity"])
            self.assertIn("Adaptive Scaffolding Agent", body1["agent_activity"])
            self.assertIn("Reflection Agent", body1["agent_activity"])
            self.assertIn("Learning Planner Agent", body1["agent_activity"])
            self.assertGreaterEqual(len(body1["similar_learners"]), 1)

            # Second attempt: Correct submission
            sub2 = client.post("/api/submit", json={
                "learner_id": learner_id,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return sum(numbers)",
                "response_time": 25.0
            })
            self.assertEqual(sub2.status_code, 200)
            body2 = sub2.json()
            self.assertTrue(body2["execution"]["passed"])
            # BKT mastery should increase upon correct submission
            self.assertGreater(body2["learner_state"]["mastery"], body1["learner_state"]["mastery"])

    def test_06_multi_turn_chat_persistence(self):
        with TestClient(app) as client:
            learner_id = "chat-tester"
            # 1. Ask question
            res1 = client.post("/api/chat", json={
                "learner_id": learner_id,
                "message": "What is the difference between a tuple and a list in Python?"
            })
            self.assertEqual(res1.status_code, 200)
            self.assertTrue(bool(res1.json()["reply"]))

            # 2. Check chat history
            hist_res = client.get(f"/api/chat/{learner_id}")
            self.assertEqual(hist_res.status_code, 200)
            messages = hist_res.json()
            self.assertGreaterEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[1]["role"], "assistant")

    def test_07_evaluation_metrics(self):
        with TestClient(app) as client:
            learner_id = "test-workflow-student"
            # 1. Fetch metrics
            m_res = client.get(f"/api/metrics/{learner_id}")
            self.assertEqual(m_res.status_code, 200)
            data = m_res.json()
            self.assertIn("learning_gain", data)
            self.assertIn("hint_efficiency", data)
            self.assertIn("task_completion_rate", data)
            self.assertIn("time_to_completion", data)

            # 2. Submit satisfaction
            sat_res = client.post("/api/metrics/satisfaction", json={
                "learner_id": learner_id,
                "score": 5
            })
            self.assertEqual(sat_res.status_code, 200)
            self.assertEqual(sat_res.json()["satisfaction_score"], 5)

    def test_08_custom_questions(self):
        with TestClient(app) as client:
            creator_id = "custom-author"
            # 1. Create question
            c_res = client.post("/api/custom-questions", json={
                "title": "Reverse a String Custom",
                "description": "Write a function `rev_str(s)` that returns reversed string.",
                "concept_id": "strings",
                "difficulty": "Easy",
                "starter_code": "def rev_str(s):\n    pass",
                "test_cases": [
                    {"input": "hello", "expected": "olleh"},
                    {"input": "python", "expected": "nohtyp"}
                ],
                "creator_id": creator_id
            })
            self.assertEqual(c_res.status_code, 200)
            q_data = c_res.json()
            self.assertEqual(q_data["title"], "Reverse a String Custom")
            self.assertTrue(q_data["is_custom"])

            # 2. Retrieve custom questions for creator
            list_res = client.get(f"/api/custom-questions/{creator_id}")
            self.assertEqual(list_res.status_code, 200)
            custom_list = list_res.json()
            self.assertGreaterEqual(len(custom_list), 1)
            self.assertEqual(custom_list[0]["creator_id"], creator_id)

    def test_09_user_isolation(self):
        with TestClient(app) as client:
            user_a = "student-alpha"
            user_b = "student-beta"

            # User A submits code
            client.post("/api/submit", json={
                "learner_id": user_a,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return sum(numbers)",
                "response_time": 12.0
            })

            # User A history
            hist_a = client.get(f"/api/history/{user_a}").json()
            # User B history
            hist_b = client.get(f"/api/history/{user_b}").json()

            self.assertGreaterEqual(len(hist_a), 1)
            self.assertEqual(len(hist_b), 0)

    def test_10_concept_wise_progress(self):
        with TestClient(app) as client:
            learner_id = "progress-student"
            # Initial concept progress fetch
            p_res = client.get(f"/api/progress/concepts/{learner_id}")
            self.assertEqual(p_res.status_code, 200)
            progress = p_res.json()
            self.assertGreaterEqual(len(progress), 40)
            self.assertIn("concept_name", progress[0])
            self.assertIn("progress_pct", progress[0])

    def test_11_dsda_scaffolding_response_structure(self):
        with TestClient(app) as client:
            learner_id = "dsda-eval-student"
            # 1. First failure submission
            sub1 = client.post("/api/submit", json={
                "learner_id": learner_id,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return -1",
                "response_time": 20.0
            })
            self.assertEqual(sub1.status_code, 200)
            data1 = sub1.json()
            scaff1 = data1["scaffolding"]
            self.assertIn(scaff1["level"], [1, 2, 3, 4])
            self.assertIn("focus", scaff1)
            self.assertIn("score", scaff1)
            self.assertIn("hint", scaff1)
            self.assertIn("rationale", scaff1)
            self.assertIn("remediation_flag", scaff1)

            # 2. Success submission clears scaffolding to Level 0
            sub2 = client.post("/api/submit", json={
                "learner_id": learner_id,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return sum(numbers)",
                "response_time": 10.0
            })
            self.assertEqual(sub2.status_code, 200)
            data2 = sub2.json()
            scaff2 = data2["scaffolding"]
            self.assertEqual(scaff2["level"], 0)
            self.assertFalse(scaff2["remediation_flag"])

    def test_12_session_lifecycle_and_recommendation_persistence(self):
        with TestClient(app) as client:
            learner_id = "session-student"
            # 1. Start session
            start_res = client.post("/api/sessions/start", json={"learner_id": learner_id})
            self.assertEqual(start_res.status_code, 200)
            sess = start_res.json()
            sess_id = sess["id"]
            self.assertEqual(sess["learner_id"], learner_id)

            # 2. List sessions
            list_res = client.get(f"/api/sessions/{learner_id}")
            self.assertEqual(list_res.status_code, 200)
            sessions = list_res.json()
            self.assertGreaterEqual(len(sessions), 1)

            # 3. End session
            end_res = client.post(f"/api/sessions/{sess_id}/end")
            self.assertEqual(end_res.status_code, 200)

            # 4. Verify recommendations endpoint
            rec_res = client.get(f"/api/learner/{learner_id}/recommendation")
            self.assertEqual(rec_res.status_code, 200)
            rec_data = rec_res.json()
            self.assertIn("next_problem_id", rec_data)
            self.assertIn("reason", rec_data)

    def test_13_problem_hints_history(self):
        with TestClient(app) as client:
            learner_id = "hints-history-student"
            # Submit failure to trigger hint generation
            client.post("/api/submit", json={
                "learner_id": learner_id,
                "problem_id": 1,
                "code": "def sum_array(numbers):\n    return 42",
                "response_time": 15.0
            })

            # Retrieve problem hints history
            h_res = client.get(f"/api/learner/{learner_id}/hints/1")
            self.assertEqual(h_res.status_code, 200)
            hints = h_res.json()
            self.assertGreaterEqual(len(hints), 1)
            self.assertIn("level", hints[0])
            self.assertIn("hint_text", hints[0])


if __name__ == "__main__":
    unittest.main()

