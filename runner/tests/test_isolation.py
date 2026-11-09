"""Security properties of the Docker backend. Each test attempts the abuse from inside the sandbox."""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUNNER_BACKEND", "docker") != "docker", reason="docker backend only")
LIMITS = {"per_test_seconds": 3, "total_seconds": 10, "memory_mb": 128, "output_kb": 32}


def value_of(run, code, limits=LIMITS):
    return run(code, limits=limits)["results"][0]


def test_no_network(run):
    code = (
        "import socket\n"
        "def solve():\n"
        "    s = socket.socket()\n    s.settimeout(1)\n"
        "    try:\n        s.connect(('1.1.1.1', 53))\n        return 'connected'\n"
        "    except OSError as e:\n        return 'blocked'\n"
    )
    assert value_of(run, code)["value"] == "blocked"


def test_no_dns_or_interfaces(run):
    code = (
        "import socket\n"
        "def solve():\n"
        "    try:\n        socket.gethostbyname('example.com')\n        return 'resolved'\n"
        "    except OSError:\n        return 'blocked'\n"
    )
    assert value_of(run, code)["value"] == "blocked"


def test_root_filesystem_is_read_only(run):
    code = (
        "def solve():\n    out = []\n"
        "    for p in ['/etc/x', '/usr/x', '/sandbox/driver.py', '/x']:\n"
        "        try:\n            open(p, 'w').write('x')\n            out.append('wrote')\n"
        "        except OSError:\n            out.append('denied')\n"
        "    return out\n"
    )
    assert value_of(run, code)["value"] == ["denied"] * 4


def test_temp_directory_is_noexec_and_size_limited(run):
    code = (
        "import os\n"
        "def solve():\n"
        "    p = '/tmp/x.sh'\n    open(p, 'w').write('#!/bin/sh\\necho hi\\n')\n    os.chmod(p, 0o755)\n"
        "    try:\n        os.execv(p, [p])\n    except OSError:\n        pass\n"
        "    return 'noexec'\n"
    )
    assert value_of(run, code)["value"] == "noexec"


def test_runs_unprivileged_with_no_capabilities(run):
    code = (
        "import os\n"
        "def solve():\n"
        "    caps = [l for l in open('/proc/self/status') if l.startswith('CapEff')][0].split()[1]\n"
        "    return [os.getuid(), os.geteuid(), int(caps, 16)]\n"
    )
    uid, euid, caps = value_of(run, code)["value"]
    assert uid == 65534 and euid == 65534 and caps == 0


def test_environment_holds_no_secrets(run):
    code = "import os\ndef solve():\n    return sorted(os.environ)\n"
    names = value_of(run, code)["value"]
    assert not [n for n in names if "TOKEN" in n or "KEY" in n or "SECRET" in n or "DATABASE" in n]


def test_cannot_read_host_files_or_harness_fds(run):
    code = (
        "import os\n"
        "def solve():\n    out = []\n"
        "    for p in ['/proc/1/mem', '/proc/1/fd/1', '/proc/1/environ', '/var/run/docker.sock']:\n"
        "        try:\n            open(p, 'rb').read(1)\n            out.append('read')\n"
        "        except OSError:\n            out.append('denied')\n"
        "    return out\n"
    )
    assert value_of(run, code)["value"] == ["denied"] * 4


def test_cannot_kill_supervisor(run):
    code = (
        "import os, signal\n"
        "def solve():\n"
        "    try:\n        os.kill(1, signal.SIGKILL)\n    except OSError:\n        pass\n"
        "    return 'alive'\n"
    )
    body = run(code, [{"id": "a", "kind": "args"}, {"id": "b", "kind": "args"}], limits=LIMITS)
    assert [r["value"] for r in body["results"]] == ["alive", "alive"]


def test_memory_bomb_is_contained(run):
    code = "def solve():\n    data = []\n    while True:\n        data.append(bytearray(10_000_000))\n"
    result = value_of(run, code)
    assert result["status"] == "memory_limit"


def test_fork_bomb_is_contained_and_service_survives(run):
    code = (
        "import os\n"
        "def solve():\n"
        "    while True:\n"
        "        try:\n            os.fork()\n        except OSError:\n            pass\n"
    )
    result = value_of(run, code, {"per_test_seconds": 2, "total_seconds": 6, "memory_mb": 128, "output_kb": 16})
    assert result["status"] in ("timeout", "crashed", "memory_limit")
    assert run("def solve():\n    return 'ok'\n")["results"][0]["value"] == "ok"


def test_background_process_does_not_outlive_its_test(run):
    code = (
        "import os, time\n"
        "def solve(mode):\n"
        "    if mode == 'spawn':\n"
        "        if os.fork() == 0:\n"
        "            open('/tmp/alive', 'w').write('x')\n"
        "            while True:\n                open('/tmp/alive', 'w').write(str(time.time()))\n                time.sleep(0.05)\n"
        "        return 'spawned'\n"
        "    before = open('/tmp/alive').read()\n    time.sleep(0.3)\n"
        "    return before == open('/tmp/alive').read()\n"
    )
    tests = [{"id": "a", "kind": "args", "args": ["spawn"]}, {"id": "b", "kind": "args", "args": ["check"]}]
    body = run(code, tests, limits=LIMITS)
    assert body["results"][1]["value"] is True


def test_container_is_removed_after_the_job(run):
    import subprocess

    body = run("def solve():\n    return 1\n")
    names = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=csmasf-job-{body['job_id']}", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    ).stdout
    assert names.strip() == ""


def test_runner_failure_is_reported_as_infrastructure(client, monkeypatch):
    import uuid

    from conftest import HEADERS

    from runner_service import config

    monkeypatch.setattr(config.settings, "sandbox_image", "csmasf-image-that-does-not-exist:none")
    job = {"job_id": uuid.uuid4().hex, "code": "x = 1", "tests": [{"id": "a", "kind": "stdio"}]}
    body = client.post("/v1/jobs", json=job, headers=HEADERS).json()
    assert body["status"] == "infrastructure_error" and body["results"] == []
