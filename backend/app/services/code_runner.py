"""Layered code execution evaluator: AST safety validation, isolated temporary subprocess execution, and test assertion verification."""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ..database import get_problem

# Legacy fallback tests for initial problems 1-5
BUILTIN_TESTS = {
    1: ("sum_array", [(([2, 3, 5],), 10), (([],), 0)]),
    2: ("find_max", [(([4, 1, 9],), 9), (([-5, -2, -8],), -2)]),
    3: ("count_vowels", [(("Education",), 5), (("sky",), 0)]),
    4: ("is_palindrome", [(("Never odd or even",), True), (("Python",), False)]),
    5: ("two_sum", [(([2, 7, 11, 15], 9), [0, 1])]),
}

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "pty", "commands",
    "posix", "winreg", "ctypes", "multiprocessing", "threading"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "__import__", "compile", "open"
}


def validate_ast_safety(code: str) -> tuple[bool, str]:
    """Layer 1 security: Inspect AST for prohibited modules, function calls, and dangerous operations."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} (line {e.lineno})"

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"Security Violation: Import of restricted module '{root_module}' is disallowed."
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"Security Violation: Import from restricted module '{root_module}' is disallowed."
        # Check dangerous built-in calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                return False, f"Security Violation: Invocation of restricted function '{node.func.id}()' is disallowed."
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen", "spawn"):
                return False, f"Security Violation: Access to system-level attribute '{node.func.attr}' is disallowed."

    return True, ""


def extract_function_name(code: str, default: str = "") -> str:
    """Extract the first top-level function definition from the code."""
    try:
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node.name
    except Exception:
        pass
    return default


def build_test_script(code: str, problem_id: int) -> str:
    """Construct an assertion verification script from database problem test cases or fallback map."""
    problem = get_problem(problem_id)
    test_cases = []
    if problem and problem.get("test_cases_json"):
        try:
            test_cases = json.loads(problem["test_cases_json"])
        except Exception:
            test_cases = []

    if test_cases:
        assertions = []
        fn_name = extract_function_name(code)
        for tc in test_cases:
            if "test_script" in tc:
                assertions.append(tc["test_script"])
            elif "input" in tc and "expected" in tc:
                args = tc["input"]
                expected = tc["expected"]
                if fn_name:
                    assertions.append(f"assert {fn_name}(*{args!r}) == {expected!r}")
        if assertions:
            return f"{code}\n\n# --- AUTOMATED TEST HARNESS ---\n" + "\n".join(assertions) + "\nprint('__ALL_TESTS_PASSED__')"

    # Fallback to BUILTIN_TESTS if available
    if problem_id in BUILTIN_TESTS:
        fn_name, cases = BUILTIN_TESTS[problem_id]
        assertions = "\n".join(f"assert {fn_name}(*{args!r}) == {expected!r}" for args, expected in cases)
        return f"{code}\n\n{assertions}\nprint('__ALL_TESTS_PASSED__')"

    # If no specific tests are defined, perform syntax & smoke check
    return f"{code}\n\nprint('__ALL_TESTS_PASSED__')"


def evaluate(code: str, problem_id: int) -> dict:
    """Layered evaluator: AST validation + isolated subprocess with strict 3-second timeout."""
    is_safe, safety_error = validate_ast_safety(code)
    if not is_safe:
        return {
            "passed": False,
            "error_type": "security" if "Security Violation" in safety_error else "syntax",
            "output": safety_error
        }

    script = build_test_script(code, problem_id)

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "submission.py"
        source_path.write_text(script, encoding="utf-8")

        # Layer 3: Restricted environment execution
        # Scrub sensitive environment variables (e.g. API keys) from child process environment
        safe_env = {
            "PYTHONPATH": "",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": temp_dir,
            "TMP": temp_dir
        }

        try:
            result = subprocess.run(
                [sys.executable, "-I", "-S", str(source_path)],
                capture_output=True,
                text=True,
                timeout=3,
                cwd=temp_dir,
                env=safe_env
            )
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "error_type": "timeout",
                "output": "Execution timed out after 3.0 seconds. Check for infinite loops or deep recursion."
            }
        except Exception as e:
            return {
                "passed": False,
                "error_type": "runtime",
                "output": f"Subprocess runner error: {str(e)[:300]}"
            }

    if result.returncode == 0 and "__ALL_TESTS_PASSED__" in result.stdout:
        return {
            "passed": True,
            "error_type": "none",
            "output": "All test assertions passed successfully."
        }

    raw_output = (result.stderr or result.stdout).strip()
    lines = [line for line in raw_output.splitlines() if line.strip()]
    last_line = lines[-1] if lines else "Non-zero exit code"

    if "AssertionError" in raw_output:
        error_type = "assertion"
    elif "SyntaxError" in raw_output:
        error_type = "syntax"
    elif "RecursionError" in raw_output:
        error_type = "recursion"
    else:
        error_type = "runtime"

    return {
        "passed": False,
        "error_type": error_type,
        "output": last_line[:400]
    }
