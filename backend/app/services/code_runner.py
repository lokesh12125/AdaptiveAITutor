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
    "eval", "exec", "__import__", "compile", "open", "getattr", "setattr", "delattr", "vars", "dir", "breakpoint"
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__bases__", "__base__", "__mro__", "__globals__", "__builtins__", "__class__", "__code__",
    "system", "popen", "spawn"
}


HARNESS_HEADER = """import sys

def _assert_equal(fn_name, fn, args, expected):
    try:
        actual = fn(*args)
    except Exception as e:
        err_type = type(e).__name__
        tb = sys.exc_info()[2]
        lineno = '?'
        while tb:
            if tb.tb_next is None:
                lineno = tb.tb_lineno
                break
            tb = tb.tb_next
        print(f"RUN_ERROR:{err_type}: {e} (line {lineno})", file=sys.stderr)
        raise

    # Normalize list/tuple comparison (e.g., tuple (2, 1) vs list [2, 1])
    is_match = False
    if actual == expected:
        is_match = True
    elif isinstance(actual, (tuple, list)) and isinstance(expected, (tuple, list)):
        is_match = list(actual) == list(expected)

    if not is_match:
        msg = f"AssertionError: Test failed for {fn_name}({', '.join(repr(a) for a in args)}). Expected {expected!r}, got {actual!r}"
        print(msg, file=sys.stderr)
        raise AssertionError(msg)
"""


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
        # Check forbidden attribute access or reflection
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                return False, f"Security Violation: Access to restricted reflection attribute '{node.attr}' is disallowed."

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

    fn_name = extract_function_name(code)

    if test_cases:
        assertions = []
        for tc in test_cases:
            if "test_script" in tc:
                assertions.append(tc["test_script"])
            elif "input" in tc and "expected" in tc:
                args = tc["input"]
                expected = tc["expected"]
                if fn_name:
                    assertions.append(f"_assert_equal({fn_name!r}, {fn_name}, {args!r}, {expected!r})")
        if assertions:
            return f"{HARNESS_HEADER}\n\n{code}\n\n# --- AUTOMATED TEST HARNESS ---\n" + "\n".join(assertions) + "\nprint('__ALL_TESTS_PASSED__')"

    # Fallback to BUILTIN_TESTS if available
    if problem_id in BUILTIN_TESTS:
        fn_name_fallback, cases = BUILTIN_TESTS[problem_id]
        target_fn = fn_name or fn_name_fallback
        assertions = "\n".join(f"_assert_equal({target_fn!r}, {target_fn}, {args!r}, {expected!r})" for args, expected in cases)
        return f"{HARNESS_HEADER}\n\n{code}\n\n# --- AUTOMATED TEST HARNESS ---\n{assertions}\nprint('__ALL_TESTS_PASSED__')"

    # If no specific tests are defined, perform syntax & smoke check
    return f"{code}\n\nprint('__ALL_TESTS_PASSED__')"


def evaluate(code: str, problem_id: int) -> dict:
    """Layered evaluator: AST validation + isolated subprocess with strict 3-second timeout."""
    is_safe, safety_error = validate_ast_safety(code)
    if not is_safe:
        return {
            "passed": False,
            "error_type": "syntax" if "SyntaxError" in safety_error else "security",
            "output": safety_error
        }

    script = build_test_script(code, problem_id)

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "submission.py"
        source_path.write_text(script, encoding="utf-8")

        # Layer 3: Restricted environment execution
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

    raw_stderr = (result.stderr or "").strip()
    raw_stdout = (result.stdout or "").strip()
    combined_output = f"{raw_stderr}\n{raw_stdout}".strip()

    # 1. Check for specific harness assertion or run error
    for line in combined_output.splitlines():
        line_s = line.strip()
        if line_s.startswith("AssertionError:"):
            return {
                "passed": False,
                "error_type": "assertion",
                "output": line_s
            }
        if line_s.startswith("RUN_ERROR:"):
            cleaned_err = line_s.replace("RUN_ERROR:", "").strip()
            err_type = cleaned_err.split(":")[0].lower() if ":" in cleaned_err else "runtime"
            return {
                "passed": False,
                "error_type": err_type,
                "output": cleaned_err
            }

    # 2. Check for standard Python exceptions in traceback
    lines = [l.strip() for l in combined_output.splitlines() if l.strip()]
    if lines:
        last_line = lines[-1]
        # Match pattern like NameError: name 'x' is not defined or SyntaxError: ...
        if ":" in last_line:
            exc_class = last_line.split(":")[0].strip()
            if exc_class in ("SyntaxError", "NameError", "TypeError", "ValueError", "IndexError", "KeyError", "AttributeError", "ZeroDivisionError", "RecursionError", "AssertionError"):
                err_type_map = {
                    "SyntaxError": "syntax",
                    "AssertionError": "assertion",
                    "RecursionError": "recursion"
                }
                # Try to extract line number from traceback lines
                lineno_str = ""
                for line in lines:
                    m = re.search(r'line (\d+)', line)
                    if m:
                        lineno_str = f" (line {m.group(1)})"
                
                output_msg = f"{last_line}{lineno_str}" if lineno_str and lineno_str not in last_line else last_line
                return {
                    "passed": False,
                    "error_type": err_type_map.get(exc_class, "runtime"),
                    "output": output_msg[:400]
                }

        return {
            "passed": False,
            "error_type": "runtime",
            "output": last_line[:400]
        }

    return {
        "passed": False,
        "error_type": "runtime",
        "output": "Execution failed with non-zero exit code."
    }
