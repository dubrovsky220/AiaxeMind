"""
Custom exceptions for LLM generation module.
"""


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class LLMConnectionError(LLMError):
    """Raised when connection to LLM provider fails."""

    def __init__(self, provider: str, original_error: Exception | None = None) -> None:
        message = f"Failed to connect to LLM provider: {provider}"
        super().__init__(message, original_error)
        self.provider = provider


class LLMAPIError(LLMError):
    """Raised when LLM API returns an error."""

    def __init__(
        self,
        status_code: int,
        error_message: str,
        original_error: Exception | None = None,
    ) -> None:
        message = f"LLM API error (status {status_code}): {error_message}"
        super().__init__(message, original_error)
        self.status_code = status_code
        self.error_message = error_message


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        message = "LLM API rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Raised when LLM API request times out."""

    def __init__(self, timeout_seconds: float) -> None:
        message = f"LLM API request timed out after {timeout_seconds}s"
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class LLMInvalidRequestError(LLMError):
    """Raised when request to LLM API is invalid."""

    def __init__(self, details: str) -> None:
        message = f"Invalid LLM request: {details}"
        super().__init__(message)
        self.details = details
