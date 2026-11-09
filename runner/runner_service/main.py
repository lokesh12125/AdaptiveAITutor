"""Internal execution API. Reachable only by the backend, which holds the shared token.

There is no endpoint for arbitrary public execution: every call needs the token, and the
service binds to loopback or an internal Compose network.
"""
from __future__ import annotations

import asyncio
import hmac
import logging

from fastapi import Depends, FastAPI, Header, HTTPException

from .backends import BackendFailure, Cancelled, build_backend, now_ms
from .config import settings
from .models import JobRequest, JobResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("runner")

if len(settings.token) < 16:
    raise RuntimeError("RUNNER_TOKEN must be set to a random value of at least 16 characters.")

app = FastAPI(title="CSMASF execution service", docs_url=None, redoc_url=None, openapi_url=None)
backend = build_backend()
slots = asyncio.Semaphore(settings.max_concurrent_jobs)
state = {"waiting": 0}


def require_token(x_runner_token: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_runner_token, settings.token):
        raise HTTPException(status_code=401, detail="invalid runner token")


@app.get("/healthz")
async def healthz() -> dict:
    status = await backend.health()
    return {"status": "ok" if status.get("ok") else "degraded", "detail": status, "isolation": backend.isolation()}


@app.post("/v1/jobs", response_model=JobResponse, dependencies=[Depends(require_token)])
async def run_job(job: JobRequest) -> JobResponse:
    started = now_ms()
    if state["waiting"] >= settings.max_queued_jobs:
        return JobResponse(
            job_id=job.job_id, status="busy", backend=backend.name, isolation=backend.isolation(),
            message="The execution service is at capacity.",
        )
    state["waiting"] += 1
    acquired = False
    try:
        await slots.acquire()
        acquired = True
        state["waiting"] -= 1
        try:
            raw = await backend.run(job)
        except Cancelled:
            return JobResponse(
                job_id=job.job_id, status="cancelled", backend=backend.name,
                isolation=backend.isolation(), duration_ms=now_ms() - started,
            )
        except BackendFailure as exc:
            log.error("job %s infrastructure failure: %s", job.job_id, exc)
            return JobResponse(
                job_id=job.job_id, status="infrastructure_error", backend=backend.name,
                isolation=backend.isolation(), message=str(exc), duration_ms=now_ms() - started,
            )
    finally:
        if acquired:
            slots.release()
        else:
            state["waiting"] -= 1
    return JobResponse(
        job_id=job.job_id, status="completed", backend=backend.name, isolation=backend.isolation(),
        results=raw.get("results", []), duration_ms=now_ms() - started,
    )


@app.post("/v1/jobs/{job_id}/cancel", dependencies=[Depends(require_token)])
async def cancel_job(job_id: str) -> dict:
    if not job_id.replace("-", "").replace("_", "").isalnum() or len(job_id) > 64:
        raise HTTPException(status_code=422, detail="invalid job id")
    await backend.cancel(job_id)
    return {"job_id": job_id, "status": "cancel_requested"}
