"""Domain exception hierarchy for ix.core.

These exceptions are framework-agnostic (no HTTP dependency).  The API layer
maps them to HTTP status codes via the exception handler in ``ix.api.main``.
"""


class IxError(Exception):
    """Base exception for all domain errors in ix.core."""


class NotFoundError(IxError):
    """Requested entity does not exist."""


class ValidationError(IxError):
    """Input failed validation."""


class DataError(IxError):
    """Data quality issue (empty series, corrupt dates, etc.)."""


class ConfigurationError(IxError):
    """Missing or invalid configuration."""


class ExpressionError(IxError):
    """Safe expression evaluation failed."""


class UploadError(ValidationError):
    """Excel / file upload parsing failed."""
