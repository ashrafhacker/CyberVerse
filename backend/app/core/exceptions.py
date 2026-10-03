class CyberVerseError(Exception):
    """Base exception for CyberVerse domain errors."""

    status_code = 400
    code = "cyberverse_error"
    message = "An error occurred"

    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(CyberVerseError):
    status_code = 404
    code = "not_found"
    message = "Resource not found"


class DuplicateError(CyberVerseError):
    status_code = 409
    code = "duplicate"
    message = "Resource already exists"


class AuthenticationError(CyberVerseError):
    status_code = 401
    code = "authentication"
    message = "Authentication failed"


class PermissionDeniedError(CyberVerseError):
    status_code = 403
    code = "permission_denied"
    message = "Insufficient permissions"


class ValidationError(CyberVerseError):
    status_code = 422
    code = "validation"
    message = "Validation failed"


class RateLimitError(CyberVerseError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests"


class PremiumRequiredError(CyberVerseError):
    status_code = 402
    code = "premium_required"
    message = "Premium subscription required"


class AccountLockedError(CyberVerseError):
    status_code = 423
    code = "account_locked"
    message = "Account is locked"


class ConflictError(CyberVerseError):
    status_code = 409
    code = "conflict"
    message = "State conflict"
