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
    "posix", "winreg", "ctypes", "multiprocessing", "threading", "_thread",
    "urllib", "requests", "http", "asyncio", "select", "fcntl", "pwd", "grp", "signal",
    "pathlib", "tempfile", "importlib", "io", "builtins", "inspect", "types",
    "pickle", "gc", "code", "codeop", "marshal", "shelve", "dbm"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "__import__", "compile", "open", "getattr", "setattr", "delattr",
    "vars", "dir", "breakpoint", "help", "input"
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__bases__", "__base__", "__mro__", "__globals__", "__builtins__",
    "__class__", "__code__", "__reduce__", "__reduce_ex__", "__loader__", "__spec__",
    "system", "popen", "spawn", "execv", "execve"
}


HARNESS_HEADER = """import sys
import builtins

# Layer 2: Runtime in-harness defense neutering network and file system access
def _blocked_open(*args, **kwargs):
    raise PermissionError("Direct file system access is prohibited in the code execution sandbox.")

builtins.open = _blocked_open

try:
    import socket
    def _blocked_socket(*args, **kwargs):
        raise PermissionError("Network socket creation is prohibited in the code execution sandbox.")
    socket.socket = _blocked_socket
except Exception:
    pass

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


def _set_subprocess_limits():
    """Apply OS-level limits within the child process before executing user code (P-04, P-06)."""
    try:
        import resource
        # CPU limit: 2s soft, 3s hard (triggers SIGXCPU/SIGKILL)
        resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
    except Exception:
        pass
    try:
        import resource
        # File creation size: max 512 KB
        resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024, 512 * 1024))
    except Exception:
        pass
    try:
        import resource
        # Open file descriptors: max 32
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    except Exception:
        pass
    try:
        import resource
        # Memory cap: max 512 MB virtual memory (RLIMIT_AS)
        mem_limit = 512 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    except Exception:
        pass
    try:
        import resource
        if hasattr(resource, "RLIMIT_NPROC"):
            # Process/thread fork cap: max 32 processes
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    except Exception:
        pass
    try:
        import os
        # Create a new session / process group so all child forks can be killed together
        os.setsid()
    except Exception:
        pass


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
        # Check access to sensitive file names or paths in constant string literals
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            val_lower = node.value.lower()
            if any(target in val_lower for target in [".auth_secret", "tutor.db", "/.ssh", "/.aws", "/etc/passwd", "/etc/shadow"]):
                return False, "Security Violation: Access to sensitive system path or application secret is prohibited."

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


def build_test_script(code: str, problem_id: int, test_cases: list = None) -> str:
    """Construct an assertion verification script from database problem test cases or fallback map."""
    if test_cases is None:
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


_SEATBELT_PROBED = False
_SEATBELT_FUNCTIONAL = False


def _check_seatbelt_usable() -> bool:
    """Probe if macOS kernel sandbox-exec is permitted in the current runtime environment."""
    global _SEATBELT_PROBED, _SEATBELT_FUNCTIONAL
    if _SEATBELT_PROBED:
        return _SEATBELT_FUNCTIONAL
    _SEATBELT_PROBED = True
    if sys.platform != "darwin":
        _SEATBELT_FUNCTIONAL = False
        return False
    sandbox_exec = Path("/usr/bin/sandbox-exec")
    if not sandbox_exec.exists():
        _SEATBELT_FUNCTIONAL = False
        return False
    try:
        res = subprocess.run(
            [str(sandbox_exec), "-p", "(version 1)\n(allow default)", sys.executable, "-c", "import sys; sys.exit(0)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0
        )
        _SEATBELT_FUNCTIONAL = (res.returncode == 0)
    except Exception:
        _SEATBELT_FUNCTIONAL = False
    return _SEATBELT_FUNCTIONAL


def get_sandbox_command(source_path: Path, temp_dir: str) -> tuple[list[str], str]:
    """
    Construct the isolated execution command based on available operating system mechanisms.
    Tiers:
    1. macOS Seatbelt kernel sandbox (/usr/bin/sandbox-exec) with strict profile denying
       network access, foreign directory write access, and sensitive host credential reading (SSH, AWS, GCloud, DB, Auth Secrets).
    2. Linux/POSIX process-group isolation with RLIMIT resource caps (CPU, Memory/AS, Files, NPROC), empty PATH, and sterile environment.
    """
    sandbox_exec = Path("/usr/bin/sandbox-exec")
    if _check_seatbelt_usable():
        home = str(Path.home())
        seatbelt_profile = (
            "(version 1)\n"
            "(allow default)\n"
            "(deny network*)\n"
            "(deny file-write*)\n"
            f'(allow file-write* (subpath "{temp_dir}"))\n'
            '(allow file-write* (subpath "/dev/null"))\n'
            '(allow file-write* (subpath "/dev/zero"))\n'
            f'(deny file-read* (subpath "{home}/.ssh"))\n'
            f'(deny file-read* (subpath "{home}/.aws"))\n'
            f'(deny file-read* (subpath "{home}/.config/gcloud"))\n'
            '(deny file-read* (regex #".*\\.auth_secret$"))\n'
            '(deny file-read* (regex #".*tutor\\.db$"))\n'
            '(deny file-read* (regex #".*\\.env$"))\n'
        )
        cmd = [
            str(sandbox_exec),
            "-p",
            seatbelt_profile,
            sys.executable,
            "-I",
            "-S",
            str(source_path)
        ]
        return cmd, "macos-seatbelt-kernel"

    cmd = [sys.executable, "-I", "-S", str(source_path)]
    return cmd, "subprocess-resource-limited"


def evaluate(code: str, problem_id: int, timeout: float = 3.0, test_cases: list = None) -> dict:
    """
    Multi-layered code evaluation engine:
    Layer 1: Static AST validation (blocking forbidden modules, calls, and reflection attributes).
    Layer 2: In-harness runtime neutering of filesystem and socket APIs.
    Layer 3: OS Seatbelt kernel sandbox (macOS /usr/bin/sandbox-exec) blocking network & unauthorized writes.
    Layer 4: OS process-group isolation (os.setsid), resource limits (RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NOFILE), empty PATH, and SIGKILL timeout cleanup.
    
    ENVIRONMENT NOTE:
    For production enterprise deployment on shared Linux clusters, student execution should be hosted in
    unprivileged containerized runtimes (e.g., Docker/gVisor/Firecracker with --net=none and read-only rootfs).
    In this local development environment, defense-in-depth isolation is strictly enforced via
    the 4-layer architecture described above.
    """
    is_safe, safety_error = validate_ast_safety(code)
    if not is_safe:
        return {
            "passed": False,
            "error_type": "syntax" if "SyntaxError" in safety_error else "security",
            "output": safety_error,
            "isolation_tier": "static-ast-enforced"
        }

    script = build_test_script(code, problem_id, test_cases=test_cases)

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "submission.py"
        source_path.write_text(script, encoding="utf-8")

        # Layer 4: Restricted environment execution (empty PATH blocks external tools)
        safe_env = {
            "PYTHONPATH": "",
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": "",
            "TEMP": temp_dir,
            "TMP": temp_dir
        }

        cmd, isolation_tier = get_sandbox_command(source_path, temp_dir)

        proc = None
        raw_stdout = ""
        raw_stderr = ""
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=temp_dir,
                env=safe_env,
                preexec_fn=_set_subprocess_limits if hasattr(os, "setsid") else None
            )
            raw_stdout, raw_stderr = proc.communicate(timeout=timeout)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            if proc:
                try:
                    import signal
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    pass
                try:
                    proc.communicate(timeout=1)
                except Exception:
                    pass
            return {
                "passed": False,
                "error_type": "timeout",
                "output": f"Execution timed out after {timeout:.1f} seconds. Check for infinite loops or deep recursion.",
                "isolation_tier": isolation_tier
            }
        except Exception as e:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            return {
                "passed": False,
                "error_type": "runtime",
                "output": f"Subprocess runner error: {str(e)[:300]}",
                "isolation_tier": isolation_tier
            }

    if returncode == 0 and "__ALL_TESTS_PASSED__" in raw_stdout:
        return {
            "passed": True,
            "error_type": "none",
            "output": "All test assertions passed successfully.",
            "isolation_tier": isolation_tier
        }

    raw_stderr = (raw_stderr or "").strip()
    raw_stdout = (raw_stdout or "").strip()
    combined_output = f"{raw_stderr}\n{raw_stdout}".strip()

    # 1. Check for specific harness assertion or run error
    for line in combined_output.splitlines():
        line_s = line.strip()
        if "PermissionError" in line_s or "Operation not permitted" in line_s or "Security Violation" in line_s:
            return {
                "passed": False,
                "error_type": "security",
                "output": f"Security Violation: Restricted resource access prohibited ({line_s})",
                "isolation_tier": isolation_tier
            }
        if line_s.startswith("AssertionError:"):
            return {
                "passed": False,
                "error_type": "assertion",
                "output": line_s,
                "isolation_tier": isolation_tier
            }
        if line_s.startswith("RUN_ERROR:"):
            cleaned_err = line_s.replace("RUN_ERROR:", "").strip()
            err_type = cleaned_err.split(":")[0].lower() if ":" in cleaned_err else "runtime"
            if err_type == "permissionerror":
                err_type = "security"
            return {
                "passed": False,
                "error_type": err_type,
                "output": cleaned_err,
                "isolation_tier": isolation_tier
            }

    # 2. Check for standard Python exceptions in traceback
    lines = [l.strip() for l in combined_output.splitlines() if l.strip()]
    if lines:
        last_line = lines[-1]
        # Check for kernel seatbelt permission errors in traceback
        if "PermissionError" in last_line or "Operation not permitted" in last_line:
            return {
                "passed": False,
                "error_type": "security",
                "output": f"Security Violation: Restricted resource access prohibited ({last_line})",
                "isolation_tier": isolation_tier
            }

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
                    "output": output_msg[:400],
                    "isolation_tier": isolation_tier
                }

        return {
            "passed": False,
            "error_type": "runtime",
            "output": last_line[:400],
            "isolation_tier": isolation_tier
        }

    return {
        "passed": False,
        "error_type": "runtime",
        "output": "Execution failed with non-zero exit code.",
        "isolation_tier": isolation_tier
    }
