"""Trusted supervisor inside the sandbox. Runs as PID 1 under Docker.

Reads one job from stdin, starts one driver process per test with its own pipes and
limits, and writes a single JSON document to its stdout. It holds no expected answers.

As PID 1 it ignores signals sent from inside the container, and it marks itself
non-dumpable so student processes (same uid) cannot read its memory or file descriptors.
"""
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time

MAX_RESULT_BYTES = 1024 * 1024
DRIVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "driver.py")


def harden_self():
    try:
        import ctypes

        PR_SET_DUMPABLE = 4
        ctypes.CDLL(None).prctl(PR_SET_DUMPABLE, 0, 0, 0, 0)
    except Exception:
        pass  # Not available on macOS; the dev backend reports reduced isolation.


def run_test(test, job, workdir):
    limits = job["limits"]
    per_test = float(limits["per_test_seconds"])
    output_cap = int(limits["output_kb"]) * 1024

    spec = {
        "kind": test["kind"],
        "code": job["code"],
        "prelude": job.get("prelude") or "",
        "function_name": job.get("function_name"),
        "args": test.get("args", []),
        "kwargs": test.get("kwargs", {}),
        "setup": test.get("setup"),
        "expr": test.get("expr"),
        "limits": {
            "cpu_seconds": max(1, int(per_test) + 1),
            "memory_mb": int(limits["memory_mb"]),
        },
    }
    result_r, result_w = os.pipe()
    spec_file = tempfile.TemporaryFile(dir=workdir)
    spec_file.write(json.dumps(spec).encode("utf-8"))
    spec_file.seek(0)
    spec_fd = spec_file.fileno()
    os.set_inheritable(spec_fd, True)

    stdin_file = tempfile.TemporaryFile(dir=workdir)
    stdin_file.write((test.get("stdin") or "").encode("utf-8"))
    stdin_file.seek(0)

    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-S", DRIVER, str(result_w), str(spec_fd)],
        stdin=stdin_file,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(result_w, spec_fd),
        start_new_session=True,
        cwd=workdir,
        env={
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PATH": "",
            "HOME": workdir,
            "TMPDIR": workdir,
        },
    )
    os.close(result_w)
    spec_file.close()
    stdin_file.close()

    buffers = {"stdout": bytearray(), "stderr": bytearray(), "result": bytearray()}
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
    selector.register(result_r, selectors.EVENT_READ, "result")

    harness_status = None
    deadline = started + per_test
    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            harness_status = "timeout"
            break
        for key, _ in selector.select(timeout=min(remaining, 0.25)):
            chunk = os.read(key.fd, 65536)
            if not chunk:
                selector.unregister(key.fileobj)
                continue
            buffers[key.data].extend(chunk)
            if key.data != "result" and len(buffers["stdout"]) + len(buffers["stderr"]) > output_cap:
                harness_status = "output_limit"
            elif key.data == "result" and len(buffers["result"]) > MAX_RESULT_BYTES:
                harness_status = "value_too_large"
        if harness_status:
            break
        if proc.poll() is not None and time.monotonic() - started > per_test:
            break

    # Kill the whole session: student code may have started children.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        returncode = proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        returncode = None
    selector.close()
    for stream in (proc.stdout, proc.stderr):
        try:
            stream.close()
        except OSError:
            pass
    try:
        os.close(result_r)
    except OSError:
        pass

    duration_ms = int((time.monotonic() - started) * 1000)
    outcome = {
        "id": test["id"],
        "duration_ms": duration_ms,
        "stdout": bytes(buffers["stdout"][:output_cap]).decode("utf-8", "replace"),
        "stderr": bytes(buffers["stderr"][:output_cap]).decode("utf-8", "replace"),
        "truncated": len(buffers["stdout"]) + len(buffers["stderr"]) > output_cap,
    }
    if harness_status:
        outcome["status"] = harness_status
        return outcome
    if buffers["result"]:
        try:
            parsed = json.loads(bytes(buffers["result"]))
            if isinstance(parsed, dict) and isinstance(parsed.get("status"), str):
                outcome.update(parsed)
                return outcome
        except ValueError:
            pass
        outcome["status"] = "invalid_result"
        return outcome
    # The process died without reporting: signals tell us why.
    if returncode in (-signal.SIGXCPU, -signal.SIGKILL) and duration_ms >= (per_test * 1000 - 50):
        outcome["status"] = "timeout"
    elif returncode == -signal.SIGKILL:
        outcome["status"] = "memory_limit"
    elif returncode == -signal.SIGXCPU:
        outcome["status"] = "timeout"
    elif returncode is not None and returncode < 0:
        outcome["status"] = "crashed"
        outcome["signal"] = -returncode
    else:
        outcome["status"] = "crashed"
    return outcome


def main():
    harden_self()
    job = json.load(sys.stdin)
    workdir = os.environ.get("SANDBOX_WORKDIR") or tempfile.mkdtemp(prefix="work", dir="/tmp")
    budget_end = time.monotonic() + float(job["limits"]["total_seconds"])
    results = []
    for test in job["tests"]:
        if time.monotonic() >= budget_end:
            results.append({"id": test["id"], "status": "skipped_time_budget", "duration_ms": 0, "stdout": "", "stderr": ""})
            continue
        results.append(run_test(test, job, workdir))
    sys.stdout.write(json.dumps({"harness": "ok", "results": results}))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
