"""CSMASF API. Serves the frontend's JSON; the execution service and databases sit behind it."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import auth, content, imports, learner, teacher, workspace
from .config import check_production_settings, settings
from .errors import ApiError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("csmasf.api")
MAX_BODY_BYTES = 1_200_000


@asynccontextmanager
async def lifespan(_: FastAPI):
    from .tutoring.service import get_graph, recover_interrupted

    if settings.is_production:
        problems = check_production_settings(settings)
        if problems:
            raise RuntimeError("Unsafe production configuration: " + " ".join(problems))
    recovered = recover_interrupted()
    if recovered:
        log.warning("Marked %d interrupted item(s) as failed after restart.", recovered)
    get_graph()
    yield


app = FastAPI(title="CSMASF Adaptive Python Tutor", version="1.0.0", lifespan=lifespan, docs_url=None if settings.is_production else "/api/docs", openapi_url=None if settings.is_production else "/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])


def _error(status: int, code: str, message: str, request: Request, details: Any = None, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, headers=headers, content={"error": {"code": code, "message": message, "details": details}, "correlation_id": getattr(request.state, "correlation_id", None)})


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.correlation_id = uuid.uuid4().hex
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return _error(413, "request_too_large", "That request is too large.", request)
    # SameSite=Lax blocks cross-site form posts. Requiring JSON also rules out simple cross-site requests.
    if request.method in ("POST", "PUT", "DELETE") and request.url.path.startswith("/api/"):
        kind = request.headers.get("content-type", "")
        if length not in (None, "0") and "application/json" not in kind:
            return _error(415, "unsupported_media_type", "Requests must be sent as JSON.", request)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message, request, exc.details, exc.headers)


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return _error(422, "invalid_request", "Some of that information does not look right.", request, details)


@app.exception_handler(StarletteHTTPException)
async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error(exc.status_code, "http_error", str(exc.detail), request)


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error (correlation %s)", getattr(request.state, "correlation_id", None))
    return _error(500, "server_error", "Something went wrong on our side. Your work is safe. Please try again.", request)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


for module in (auth, content, workspace, learner, teacher, imports):
    app.include_router(module.router)
