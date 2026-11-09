"""Runs one test in one short-lived process. It executes *untrusted* student code.

The driver never receives expected answers. It only reports what the code produced,
so tampering with this process cannot produce a passing grade: grading happens outside
the sandbox, in the backend, against answers that never enter this container.
"""
import json
import os
import sys
import traceback

STUDENT_FILE = "solution.py"
MAX_VALUE_NODES = 20000
MAX_TEXT = 2000


def apply_limits(spec):
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return
    limits = spec.get("limits", {})
    cpu = int(limits.get("cpu_seconds", 3))
    mem = int(limits.get("memory_mb", 128)) * 1024 * 1024
    for name, value in (
        ("RLIMIT_CPU", (cpu, cpu + 1)),
        ("RLIMIT_AS", (mem, mem)),
        ("RLIMIT_FSIZE", (1024 * 1024, 1024 * 1024)),
        ("RLIMIT_NOFILE", (64, 64)),
        ("RLIMIT_CORE", (0, 0)),
    ):
        try:
            resource.setrlimit(getattr(resource, name), value)
        except (ValueError, OSError, AttributeError):
            pass  # macOS rejects RLIMIT_AS; the dev backend reports this limitation.


class TooLarge(Exception):
    pass


def encode(value, budget=None, depth=0):
    """Encode a Python value as tagged JSON so tuples, sets and non-string keys survive."""
    budget = budget if budget is not None else [MAX_VALUE_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > 200:
        raise TooLarge()
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and len(value) > 200000:
            raise TooLarge()
        return value
    if isinstance(value, int):
        return value if abs(value) < 10**300 else {"$bigint": str(value)[:4000]}
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return {"$float": repr(value)}
        return value
    if isinstance(value, list):
        return [encode(v, budget, depth + 1) for v in value]
    if isinstance(value, tuple):
        return {"$tuple": [encode(v, budget, depth + 1) for v in value]}
    if isinstance(value, (set, frozenset)):
        items = [encode(v, budget, depth + 1) for v in value]
        return {"$set": sorted(items, key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, dict):
        items = [[encode(k, budget, depth + 1), encode(v, budget, depth + 1)] for k, v in value.items()]
        return {"$dict": sorted(items, key=lambda x: json.dumps(x[0], sort_keys=True))}
    if isinstance(value, (bytes, bytearray)):
        return {"$bytes": bytes(value)[:4096].hex()}
    if isinstance(value, range) or type(value).__name__ in ("generator", "map", "filter", "zip"):
        return {"$opaque": type(value).__name__}
    try:
        text = repr(value)[:MAX_TEXT]
    except BaseException:
        text = "<unprintable>"
    return {"$repr": text, "$type": type(value).__name__}


def describe_exception(exc):
    frames = []
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == STUDENT_FILE:
            frames.append({"line": frame.lineno, "function": frame.name})
    try:
        message = str(exc)[:MAX_TEXT]
    except BaseException:
        message = ""
    return {
        "type": type(exc).__name__,
        "message": message,
        "line": frames[-1]["line"] if frames else None,
        "frames": frames[-8:],
    }


def syntax_error_info(exc):
    return {
        "type": type(exc).__name__,
        "message": str(getattr(exc, "msg", "") or exc)[:MAX_TEXT],
        "line": getattr(exc, "lineno", None),
        "column": getattr(exc, "offset", None),
        "end_line": getattr(exc, "end_lineno", None),
        "text": (getattr(exc, "text", "") or "").rstrip("\n")[:300],
    }


def main():
    result_fd, spec_fd = int(sys.argv[1]), int(sys.argv[2])
    with os.fdopen(spec_fd, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    result_stream = os.fdopen(result_fd, "w", encoding="utf-8")
    apply_limits(spec)

    def finish(payload):
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except BaseException:
            pass
        try:
            result_stream.write(json.dumps(payload))
            result_stream.flush()
        except BaseException:
            pass
        os._exit(0)

    kind = spec["kind"]
    namespace = {"__name__": "__main__" if kind == "stdio" else "solution", "__file__": STUDENT_FILE}

    prelude = spec.get("prelude") or ""
    if prelude:
        exec(compile(prelude, "<prelude>", "exec"), namespace)

    source = spec["code"]
    try:
        compiled = compile(source, STUDENT_FILE, "exec")
    except (SyntaxError, ValueError) as exc:
        finish({"status": "syntax_error", "error": syntax_error_info(exc)})

    try:
        exec(compiled, namespace)
    except SystemExit as exc:
        if kind == "stdio" and exc.code in (None, 0):
            finish({"status": "ok", "value": None})
        finish({"status": "exception", "phase": "module", "error": describe_exception(exc)})
    except MemoryError as exc:
        finish({"status": "memory_limit", "error": describe_exception(exc)})
    except BaseException as exc:
        finish({"status": "exception", "phase": "module", "error": describe_exception(exc)})

    if kind == "stdio":
        finish({"status": "ok", "value": None})

    try:
        if kind == "args":
            name = spec.get("function_name") or ""
            function = namespace.get(name)
            if not callable(function):
                finish({"status": "missing_function", "name": name})
            value = function(*spec.get("args", []), **spec.get("kwargs", {}))
        elif kind == "expr":
            if spec.get("setup"):
                exec(compile(spec["setup"], "<test-setup>", "exec"), namespace)
            value = eval(compile(spec["expr"], "<test-expr>", "eval"), namespace)
        else:
            finish({"status": "bad_test", "reason": f"unknown kind {kind!r}"})
    except SystemExit as exc:
        finish({"status": "exception", "phase": "call", "error": describe_exception(exc)})
    except MemoryError as exc:
        finish({"status": "memory_limit", "error": describe_exception(exc)})
    except BaseException as exc:
        finish({"status": "exception", "phase": "call", "error": describe_exception(exc)})

    try:
        encoded = encode(value)
    except TooLarge:
        finish({"status": "value_too_large"})
    except RecursionError:
        finish({"status": "value_too_large"})
    except MemoryError as exc:
        finish({"status": "memory_limit", "error": describe_exception(exc)})
    except BaseException as exc:
        finish({"status": "exception", "phase": "encode", "error": describe_exception(exc)})
    finish({"status": "ok", "value": encoded})


if __name__ == "__main__":
    main()
