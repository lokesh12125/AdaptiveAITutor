"""Behaviour every backend must honour: learners' code outcomes are classified correctly."""
import os

SHORT = {"per_test_seconds": 1.5, "total_seconds": 8, "memory_mb": 128, "output_kb": 16}
IS_DOCKER = os.environ.get("RUNNER_BACKEND", "docker") == "docker"


def first(body):
    return body["results"][0]


def test_requires_token(client):
    response = client.post("/v1/jobs", json={"job_id": "abcdefgh12", "code": "", "tests": [{"id": "a", "kind": "stdio"}]})
    assert response.status_code == 401


def test_correct_code_returns_value(run):
    result = first(run("def solve(a, b):\n    return a + b\n", [{"id": "t", "kind": "args", "args": [2, 3]}]))
    assert result["status"] == "ok" and result["value"] == 5


def test_wrong_answer_is_just_a_value(run):
    # The sandbox has no expected answers; it can only report what was returned.
    result = first(run("def solve():\n    return 41\n"))
    assert result["status"] == "ok" and result["value"] == 41


def test_values_keep_their_python_type(run):
    code = "def solve():\n    return (1, [2], {3}, {4: 'x'}, None, True, 1.5)\n"
    value = first(run(code))["value"]
    assert value == {"$tuple": [1, [2], {"$set": [3]}, {"$dict": [[4, "x"]]}, None, True, 1.5]}


def test_syntax_error_has_real_location(run):
    result = first(run("def solve():\n    x = 1\n    if x\n        return 2\n"))
    assert result["status"] == "syntax_error"
    assert result["error"]["line"] == 3 and result["error"]["type"] == "SyntaxError"


def test_indentation_error_is_syntax(run):
    result = first(run("def solve():\nreturn 1\n"))
    assert result["status"] == "syntax_error" and result["error"]["type"] == "IndentationError"


def test_runtime_exception_reports_student_line_only(run):
    result = first(run("def solve():\n    a = [1]\n    return a[5]\n"))
    assert result["status"] == "exception"
    assert result["error"]["type"] == "IndexError" and result["error"]["line"] == 3
    assert all(frame["function"] in ("solve", "<module>") for frame in result["error"]["frames"])


def test_module_level_exception(run):
    result = first(run("raise ValueError('boom')\n"))
    assert result["status"] == "exception" and result["phase"] == "module"
    assert result["error"]["type"] == "ValueError" and result["error"]["line"] == 1


def test_missing_function(run):
    result = first(run("def other():\n    return 1\n"))
    assert result["status"] == "missing_function" and result["name"] == "solve"


def test_infinite_loop_times_out_and_later_tests_still_run(run):
    code = "def solve(spin):\n    while spin:\n        pass\n    return 'done'\n"
    body = run(code, [{"id": "a", "kind": "args", "args": [True]}, {"id": "b", "kind": "args", "args": [False]}], limits=SHORT)
    assert body["results"][0]["status"] == "timeout"
    assert body["results"][1]["status"] == "ok" and body["results"][1]["value"] == "done"


def test_excessive_output_is_stopped(run):
    result = first(run("def solve():\n    while True:\n        print('x' * 1000)\n", limits=SHORT))
    assert result["status"] == "output_limit"
    assert len(result["stdout"]) <= 16 * 1024


def test_stdout_and_stdin_mode(run):
    tests = [{"id": "s", "kind": "stdio", "stdin": "4\n5\n"}]
    result = first(run("a = int(input())\nb = int(input())\nprint(a * b)\n", tests, function_name=None))
    assert result["status"] == "ok" and result["stdout"] == "20\n"


def test_input_past_eof_is_a_learner_error(run):
    tests = [{"id": "s", "kind": "stdio", "stdin": ""}]
    result = first(run("x = input()\n", tests, function_name=None))
    assert result["status"] == "exception" and result["error"]["type"] == "EOFError"


def test_expression_tests_use_prelude_and_setup(run):
    prelude = "class Node:\n    def __init__(self, v):\n        self.v = v\n"
    tests = [{"id": "e", "kind": "expr", "setup": "n = Node(7)", "expr": "get(n)"}]
    result = first(run("def get(node):\n    return node.v\n", tests, prelude=prelude))
    assert result["status"] == "ok" and result["value"] == 7


def test_each_test_is_a_fresh_process(run):
    code = "seen = []\ndef solve():\n    seen.append(1)\n    return len(seen)\n"
    body = run(code, [{"id": "a", "kind": "args"}, {"id": "b", "kind": "args"}])
    assert [r["value"] for r in body["results"]] == [1, 1]


def test_recursion_error_is_a_normal_exception(run):
    result = first(run("def solve():\n    return solve()\n"))
    assert result["status"] == "exception" and result["error"]["type"] == "RecursionError"


def test_value_too_large_is_contained(run):
    result = first(run("def solve():\n    return list(range(100000))\n"))
    assert result["status"] == "value_too_large"


def test_total_time_budget_skips_remaining_tests(run):
    limits = {"per_test_seconds": 1, "total_seconds": 1.5, "memory_mb": 128, "output_kb": 16}
    code = "def solve():\n    while True:\n        pass\n"
    body = run(code, [{"id": str(i), "kind": "args"} for i in range(5)], limits=limits)
    assert {"timeout", "skipped_time_budget"} == {r["status"] for r in body["results"]}


def test_faking_a_pass_gains_nothing(run):
    # The attack that defeated the previous runner: print the success marker and exit cleanly.
    code = "print('__ALL_TESTS_PASSED__')\nraise SystemExit(0)\n"
    result = first(run(code))
    assert result["status"] == "exception" and result["error"]["type"] == "SystemExit"
    assert result["value"] is None


def test_student_cannot_write_to_the_harness_output(run):
    code = (
        "import sys\nimport os\n"
        "def solve():\n"
        "    try:\n"
        "        os.write(1, b'{\"harness\": \"ok\", \"results\": []}')\n"
        "    except OSError:\n"
        "        pass\n"
        "    return 1\n"
    )
    body = run(code)
    assert len(body["results"]) == 1 and body["results"][0]["value"] == 1


def test_dev_backend_is_never_reported_as_secure(client):
    from runner_service import main

    isolation = main.backend.isolation()
    if not IS_DOCKER:
        assert isolation["secure"] is False and "not isolated" in isolation["label"]
    else:
        assert isolation["secure"] is True


def test_dev_backend_blocks_network_and_home_on_macos(run):
    import sys

    if IS_DOCKER or sys.platform != "darwin":
        return
    code = (
        "import socket, os\n"
        "def solve():\n"
        "    out = []\n"
        "    try:\n        socket.create_connection(('1.1.1.1', 53), timeout=1)\n        out.append('connected')\n"
        "    except OSError:\n        out.append('blocked')\n"
        f"    try:\n        open({os.path.expanduser('~/.zshrc')!r}).read(1)\n        out.append('read')\n"
        "    except OSError:\n        out.append('blocked')\n"
        "    return out\n"
    )
    assert first(run(code))["value"] == ["blocked", "blocked"]


def test_trace_records_values_on_chosen_lines(run):
    code = "def solve(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
    body = run(code, tests=[{"id": "t1", "kind": "args", "args": [3], "trace_lines": [4]}])
    outcome = body["results"][0]
    assert outcome["status"] == "ok" and outcome["value"] == 3, "tracing does not change the result"
    assert [e["vars"]["i"] for e in outcome["trace"]] == ["1", "2"]
    assert outcome["trace"][0]["line"] == 4 and outcome["trace"][0]["vars"]["total"] == "0"


def test_trace_of_a_line_that_never_runs_is_empty(run):
    body = run("def solve(n):\n    return n\n    n = 1\n", tests=[{"id": "t1", "kind": "args", "args": [3], "trace_lines": [3]}])
    assert body["results"][0]["trace"] == []


def test_trace_is_bounded_and_absent_when_not_requested(run):
    body = run("def solve(n):\n    for i in range(100000):\n        n += i\n    return n\n", tests=[{"id": "t1", "kind": "args", "args": [1], "trace_lines": [3]}, {"id": "t2", "kind": "args", "args": [1]}])
    assert len(body["results"][0]["trace"]) == 40
    assert body["results"][1].get("trace") is None


def test_trace_survives_hostile_values(run):
    code = "class Bad:\n    def __repr__(self):\n        raise RuntimeError('no')\n\ndef solve():\n    x = Bad()\n    y = 'z' * 5000\n    return 1\n"
    body = run(code, tests=[{"id": "t1", "kind": "args", "args": [], "trace_lines": [8]}])
    event = body["results"][0]["trace"][0]
    assert event["vars"]["x"] == "<unprintable>" and len(event["vars"]["y"]) == 80

