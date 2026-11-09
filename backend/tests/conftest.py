"""Integration tests use a dedicated PostgreSQL database and the real execution service."""
import os
import tempfile
import time
import uuid
from pathlib import Path

os.environ.update(
    DATABASE_URL="postgresql+psycopg://csmasf:csmasf_dev_password@127.0.0.1:5544/csmasf_test",
    CHROMA_PATH=tempfile.mkdtemp(prefix="csmasf-chroma-"),
    LLM_PROVIDER="none",
    DEMO_MODE="true",
    RETRIEVAL_ALLOW_SYNTHETIC="true",
    TEACHER_INVITE_CODE="test-invite",
    ENVIRONMENT="development",
    RATE_RUN_PER_MINUTE="100000",
    RATE_SUBMIT_PER_MINUTE="100000",
    RATE_HINT_PER_MINUTE="100000",
    RATE_AUTH_PER_MINUTE="100000",
    RATE_IMPORT_PER_MINUTE="100000",
)

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent


def _reset_database() -> None:
    admin = psycopg.connect("postgresql://csmasf:csmasf_dev_password@127.0.0.1:5544/postgres", autocommit=True)
    admin.execute("DROP DATABASE IF EXISTS csmasf_test WITH (FORCE)")
    admin.execute("CREATE DATABASE csmasf_test")
    admin.close()


@pytest.fixture(scope="session")
def app_ready():
    _reset_database()
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(config, "head")
    from app.seed import seed_content, seed_demo_class, seed_synthetic_cases

    seed_content()
    seed_synthetic_cases(400)
    seed_demo_class()
    from app.main import app

    yield app


@pytest.fixture(scope="session")
def anon(app_ready):
    with TestClient(app_ready) as client:
        yield client


class Learner:
    def __init__(self, app, name="Test Learner", role="student", invite=None):
        self.client = TestClient(app)
        self.email = f"{uuid.uuid4().hex[:12]}@example.com"
        self.password = "correct horse battery"
        body = {"name": name, "email": self.email, "password": self.password, "role": role}
        if invite:
            body["invite_code"] = invite
        response = self.client.post("/api/auth/register", json=body)
        assert response.status_code == 201, response.text
        self.id = response.json()["id"]

    @staticmethod
    def key() -> str:
        return uuid.uuid4().hex

    def run(self, problem, code, **extra):
        response = self.client.post(f"/api/problems/{problem}/run", json={"code": code, "idempotency_key": self.key(), **extra})
        assert response.status_code == 202, response.text
        return self.wait_evaluation(response.json()["id"])

    def submit(self, problem, code, wait=True, key=None, **extra):
        response = self.client.post(f"/api/problems/{problem}/submit", json={"code": code, "idempotency_key": key or self.key(), **extra})
        assert response.status_code == 202, response.text
        return self.wait_run(response.json()["id"]) if wait else response.json()

    def hint(self, problem, code, wait=True, **extra):
        response = self.client.post(f"/api/problems/{problem}/hint", json={"code": code, "idempotency_key": self.key(), **extra})
        assert response.status_code == 202, response.text
        return self.wait_run(response.json()["id"]) if wait else response.json()

    def wait_run(self, run_id, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            body = self.client.get(f"/api/runs/{run_id}").json()
            if body["status"] in ("completed", "failed"):
                return body
            time.sleep(0.1)
        raise AssertionError(f"run {run_id} did not finish: {body}")

    def wait_evaluation(self, evaluation_id, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            body = self.client.get(f"/api/evaluations/{evaluation_id}").json()
            if body["status"] in ("completed", "failed", "cancelled"):
                return body
            time.sleep(0.1)
        raise AssertionError(f"evaluation {evaluation_id} did not finish")


@pytest.fixture
def make_learner(app_ready, anon):
    def _make(**kwargs):
        return Learner(app_ready, **kwargs)

    return _make


@pytest.fixture
def learner(make_learner):
    return make_learner()


class ScriptedProvider:
    """A stand-in model. Returns scripted text in order, or raises to simulate an outage."""

    name = "scripted"
    model = "scripted-model"

    def __init__(self, replies=None, fail=False):
        self.replies = list(replies or [])
        self.fail = fail
        self.calls = []

    def complete(self, system, user, max_tokens, temperature):
        from app.tutoring.llm import LLMResult, LLMUnavailable

        self.calls.append({"system": system, "user": user})
        if self.fail:
            raise LLMUnavailable("simulated outage")
        text = self.replies.pop(0) if self.replies else '{"message": "What does your code do on the first example?", "question": "What did you expect?"}'
        return LLMResult(text, self.name, self.model, 5, {})


@pytest.fixture
def scripted_model(monkeypatch):
    from app.tutoring.llm import gateway

    def _install(replies=None, fail=False):
        provider = ScriptedProvider(replies, fail)
        monkeypatch.setattr(gateway, "provider", provider)
        return provider

    return _install
