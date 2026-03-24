"""Standardized API exception hierarchy.

All exceptions carry a machine-readable ``code`` and human-readable ``detail``.
FastAPI exception handlers in ``main.py`` convert these to consistent JSON:
    {"detail": "...", "code": "NOT_FOUND"}
"""

from fastapi import HTTPException


class AppError(HTTPException):
    """Base application error with a machine-readable code."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
        code: str = "INTERNAL_ERROR",
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail, code="NOT_FOUND")


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=400, detail=detail, code="VALIDATION_ERROR")


class AuthError(AppError):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail, code="AUTH_ERROR")


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=403, detail=detail, code="FORBIDDEN")


class RateLimitError(AppError):
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail, code="RATE_LIMITED")
