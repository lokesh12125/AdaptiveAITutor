from typing import Any, Literal

from pydantic import BaseModel, Field


class Limits(BaseModel):
    per_test_seconds: float = Field(default=2.0, gt=0, le=10)
    total_seconds: float = Field(default=12.0, gt=0, le=30)
    memory_mb: int = Field(default=192, ge=32, le=256)
    output_kb: int = Field(default=64, ge=1, le=256)


class TestSpec(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    kind: Literal["args", "expr", "stdio"]
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    setup: str | None = Field(default=None, max_length=20000)
    expr: str | None = Field(default=None, max_length=4000)
    stdin: str | None = Field(default=None, max_length=1_000_000)
    trace_lines: list[int] | None = Field(default=None, max_length=30)


class JobRequest(BaseModel):
    job_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    language: Literal["python"] = "python"
    code: str = Field(max_length=64000)
    prelude: str | None = Field(default=None, max_length=20000)
    function_name: str | None = Field(default=None, max_length=120)
    tests: list[TestSpec] = Field(min_length=1, max_length=120)
    limits: Limits = Field(default_factory=Limits)


class TestOutcome(BaseModel):
    id: str
    status: str
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    value: Any = None
    error: dict[str, Any] | None = None
    phase: str | None = None
    name: str | None = None
    signal: int | None = None
    trace: list[dict[str, Any]] | None = None


class JobResponse(BaseModel):
    job_id: str
    status: Literal["completed", "infrastructure_error", "cancelled", "busy"]
    backend: str
    isolation: dict[str, Any]
    results: list[TestOutcome] = Field(default_factory=list)
    message: str | None = None
    duration_ms: int = 0
