"""Execution backends. A backend starts the harness, feeds it a job, returns its raw JSON."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import time

from .config import settings
from .models import JobRequest

log = logging.getLogger("runner.backend")
MAX_HARNESS_OUTPUT = 32 * 1024 * 1024


class BackendFailure(Exception):
    """The execution infrastructure failed. This is never the learner's fault."""


class Cancelled(Exception):
    pass


async def _communicate(proc: asyncio.subprocess.Process, payload: bytes, timeout: float) -> bytes:
    async def feed_and_read() -> bytes:
        assert proc.stdin and proc.stdout
        try:
            proc.stdin.write(payload)
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.stdin.close()
        out = bytearray()
        while True:
            chunk = await proc.stdout.read(1024 * 256)
            if not chunk:
                break
            out.extend(chunk)
            if len(out) > MAX_HARNESS_OUTPUT:
                raise BackendFailure("harness produced too much data")
        await proc.wait()
        return bytes(out)

    return await asyncio.wait_for(feed_and_read(), timeout=timeout)


class DockerBackend:
    name = "docker"

    def __init__(self) -> None:
        self._cancelled: set[str] = set()

    def isolation(self) -> dict:
        return {
            "backend": self.name,
            "secure": True,
            "label": "Isolated container",
            "properties": {
                "network": "disabled",
                "root_filesystem": "read-only",
                "user": "65534 (unprivileged)",
                "capabilities": "all dropped",
                "memory_mb": settings.container_memory_mb,
                "pids": settings.container_pids,
                "cpus": settings.container_cpus,
            },
            "note": "Verified by the runner test suite on this host. Not independently audited for hostile production use.",
        }

    def _command(self, job_id: str) -> list[str]:
        memory = f"{settings.container_memory_mb}m"
        return [
            settings.docker_binary, "run", "--rm", "-i",
            "--name", f"csmasf-job-{job_id}",
            "--pull", "never",
            "--network", "none",
            "--read-only",
            "--tmpfs", f"/tmp:rw,noexec,nosuid,nodev,size={settings.tmpfs_mb}m,mode=1777",
            "--memory", memory, "--memory-swap", memory,
            "--cpus", settings.container_cpus,
            "--pids-limit", str(settings.container_pids),
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--ipc", "private",
            "--user", "65534:65534",
            "--ulimit", "core=0",
            "--ulimit", "nofile=128:128",
            "--log-driver", "none",
            "--hostname", "sandbox",
            settings.sandbox_image,
        ]

    async def _kill(self, job_id: str) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                settings.docker_binary, "kill", f"csmasf-job-{job_id}",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception as exc:  # noqa: BLE001 - best effort cleanup
            log.warning("docker kill failed for %s: %s", job_id, type(exc).__name__)

    async def cancel(self, job_id: str) -> None:
        self._cancelled.add(job_id)
        await self._kill(job_id)

    async def run(self, job: JobRequest) -> dict:
        payload = job.model_dump_json().encode("utf-8")
        hard_timeout = job.limits.total_seconds + 12  # startup, plus the last test finishing
        try:
            proc = await asyncio.create_subprocess_exec(
                *self._command(job.job_id),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (FileNotFoundError, PermissionError) as exc:
            raise BackendFailure(f"docker unavailable: {type(exc).__name__}") from exc

        try:
            output = await _communicate(proc, payload, hard_timeout)
        except TimeoutError as exc:
            await self._kill(job.job_id)
            raise BackendFailure("sandbox exceeded the hard time limit") from exc

        if job.job_id in self._cancelled:
            self._cancelled.discard(job.job_id)
            raise Cancelled()
        if proc.returncode != 0 or not output:
            stderr = b""
            if proc.stderr:
                stderr = await proc.stderr.read(2000)
            log.error("sandbox exit=%s stderr=%s", proc.returncode, stderr[:500])
            raise BackendFailure(f"sandbox exited with status {proc.returncode}")
        try:
            return json.loads(output)
        except ValueError as exc:
            raise BackendFailure("sandbox returned malformed output") from exc

    async def health(self) -> dict:
        try:
            proc = await asyncio.create_subprocess_exec(
                settings.docker_binary, "image", "inspect", settings.sandbox_image, "--format", "{{.Id}}",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"docker not reachable ({type(exc).__name__})"}
        if proc.returncode != 0:
            return {"ok": False, "reason": f"sandbox image {settings.sandbox_image} not found"}
        return {"ok": True, "image_id": out.decode().strip()[:24]}


SEATBELT_PROFILE = """(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "{work}") (literal "/dev/null") (literal "/dev/zero"))
(deny file-read-data (subpath "{home}"))
(allow file-read-data (subpath "{python_prefix}") (subpath "{python_base}") (subpath "{harness}") (subpath "{work}"))
"""


class LocalDevUnsafeBackend:
    """Explicit opt-in for machines without Docker. Reduced isolation and clearly reported as such."""

    name = "local_dev_unsafe"

    def __init__(self) -> None:
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._cancelled: set[str] = set()

    def isolation(self) -> dict:
        return {
            "backend": self.name,
            "secure": False,
            "label": "Development mode: not isolated",
            "properties": {"network": "denied by a macOS sandbox profile where available", "home_folder": "unreadable where the profile applies"},
            "note": "A host subprocess, with a macOS sandbox profile where available. No memory or process limits are enforced on macOS, and on other systems there is no sandbox at all. Use on your own machine only, with code you trust.",
        }

    async def cancel(self, job_id: str) -> None:
        self._cancelled.add(job_id)
        proc = self._procs.get(job_id)
        if proc and proc.returncode is None:
            proc.kill()

    async def run(self, job: JobRequest) -> dict:
        harness_dir = settings.dev_harness_dir.resolve()
        payload = job.model_dump_json().encode("utf-8")
        work = os.path.realpath(tempfile.mkdtemp(prefix="csmasf-dev-"))
        env = {"SANDBOX_WORKDIR": work, "PATH": "", "HOME": work, "TMPDIR": work}
        command = [sys.executable, "-I", "-S", str(harness_dir / "harness.py")]
        if sys.platform == "darwin" and os.path.exists("/usr/bin/sandbox-exec"):
            profile = SEATBELT_PROFILE.format(
                home=os.path.realpath(os.path.expanduser("~")),
                python_prefix=os.path.realpath(sys.prefix),
                python_base=os.path.realpath(sys.base_prefix),
                harness=harness_dir,
                work=work,
            )
            command = ["/usr/bin/sandbox-exec", "-p", profile, *command]
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=env, cwd=work, start_new_session=True,
            )
            self._procs[job.job_id] = proc
            try:
                output = await _communicate(proc, payload, job.limits.total_seconds + 6)
            except TimeoutError as exc:
                proc.kill()
                raise BackendFailure("harness exceeded the hard time limit") from exc
        finally:
            self._procs.pop(job.job_id, None)
            shutil.rmtree(work, ignore_errors=True)
        if job.job_id in self._cancelled:
            self._cancelled.discard(job.job_id)
            raise Cancelled()
        if proc.returncode != 0 or not output:
            stderr = await proc.stderr.read(1000) if proc.stderr else b""
            log.error("dev harness exit=%s stderr=%s", proc.returncode, stderr[:400])
            raise BackendFailure(f"harness exited with status {proc.returncode}")
        try:
            return json.loads(output)
        except ValueError as exc:
            raise BackendFailure("harness returned malformed output") from exc

    async def health(self) -> dict:
        return {"ok": True, "warning": "not isolated"}


def build_backend():
    if settings.backend == "docker":
        return DockerBackend()
    if settings.backend == "local_dev_unsafe":
        log.warning("RUNNER_BACKEND=local_dev_unsafe: student code is NOT isolated.")
        return LocalDevUnsafeBackend()
    raise RuntimeError(f"Unknown RUNNER_BACKEND {settings.backend!r}")


def now_ms() -> int:
    return int(time.monotonic() * 1000)
