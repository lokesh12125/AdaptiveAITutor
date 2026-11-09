"""Boundary to the isolated execution service. Failures here are never treated as learner mistakes."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("csmasf.runner")


@dataclass
class RunnerResult:
    status: str  # completed | infrastructure_error | cancelled | busy
    results: list[dict[str, Any]] = field(default_factory=list)
    backend: str | None = None
    secure: bool | None = None
    message: str | None = None
    duration_ms: int = 0


class RunnerClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            base_url=settings.runner_url, timeout=settings.runner_timeout_seconds, transport=transport,
            headers={"X-Runner-Token": settings.runner_token},
        )

    def execute(self, job: dict[str, Any]) -> RunnerResult:
        try:
            response = self._client.post("/v1/jobs", json=job)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.error("execution service request failed: %s", type(exc).__name__)
            return RunnerResult(status="infrastructure_error", message="The execution service could not be reached.")
        isolation = body.get("isolation") or {}
        return RunnerResult(
            status=body.get("status", "infrastructure_error"), results=body.get("results", []),
            backend=isolation.get("backend"), secure=isolation.get("secure"),
            message=body.get("message"), duration_ms=body.get("duration_ms", 0),
        )

    def cancel(self, job_id: str) -> None:
        try:
            self._client.post(f"/v1/jobs/{job_id}/cancel", timeout=5)
        except httpx.HTTPError as exc:
            log.warning("cancel failed: %s", type(exc).__name__)

    def health(self) -> dict[str, Any]:
        try:
            response = self._client.get("/healthz", timeout=8)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {"status": "unreachable", "detail": {"reason": type(exc).__name__}, "isolation": None}


runner = RunnerClient()
