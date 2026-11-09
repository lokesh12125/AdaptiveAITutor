"""Structured API errors: {"error": {"code", "message", "details"}, "correlation_id"}."""
from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None,
                 headers: dict[str, str] | None = None) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str = "That item") -> ApiError:
    return ApiError(404, "not_found", f"{what} could not be found.")


def forbidden(message: str = "You do not have access to this.") -> ApiError:
    return ApiError(403, "forbidden", message)
