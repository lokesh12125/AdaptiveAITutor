import os
import subprocess
import uuid

import pytest

os.environ.setdefault("RUNNER_TOKEN", "test-token-test-token")
os.environ.setdefault("RUNNER_BACKEND", "docker")

from fastapi.testclient import TestClient

from runner_service.main import app

HEADERS = {"X-Runner-Token": os.environ["RUNNER_TOKEN"]}


def docker_ready() -> bool:
    try:
        return subprocess.run(
            ["docker", "image", "inspect", "csmasf-sandbox:py312"],
            capture_output=True, timeout=10,
        ).returncode == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def client():
    if os.environ["RUNNER_BACKEND"] == "docker" and not docker_ready():
        pytest.fail("Docker sandbox image is missing. Run: docker build -t csmasf-sandbox:py312 runner/sandbox")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def run(client):
    def _run(code, tests=None, function_name="solve", prelude=None, limits=None, expect_status="completed"):
        job = {
            "job_id": uuid.uuid4().hex,
            "code": code,
            "function_name": function_name,
            "prelude": prelude,
            "tests": tests or [{"id": "t1", "kind": "args", "args": []}],
        }
        if limits:
            job["limits"] = limits
        response = client.post("/v1/jobs", json=job, headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == expect_status, body
        return body

    return _run
