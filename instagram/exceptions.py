class ActionEngineError(Exception):
    """Base exception for the outbound action engine."""


class ValidationError(ActionEngineError):
    """Raised when action payload validation fails."""


class DeliveryError(ActionEngineError):
    """Raised when delivery verification fails after execution."""


class RateLimitError(ActionEngineError):
    """Raised when a rate‑limit would be exceeded. Handled by retry/back‑off logic."""


class RetryExhaustedError(ActionEngineError):
    """Raised after the maximum number of retry attempts has been exhausted."""


# ── Instagram session / API exceptions ────────────────────────────────────────

class InstagramException(Exception):
    """Base exception for Instagram-related errors."""


class InstagramRateLimitException(InstagramException):
    """Raised when Instagram imposes a rate limit."""


class InstagramChallengeException(InstagramException):
    """Raised when Instagram requires a challenge (e.g. CAPTCHA / email code)."""

    def __init__(self, message: str = "", challenge_url: str = ""):
        super().__init__(message)
        self.challenge_url = challenge_url


class InstagramTwoFactorRequiredException(InstagramException):
    """Raised when Instagram requires two-factor authentication."""

    def __init__(self, message: str = "", two_factor_info: dict = None):
        super().__init__(message)
        self.two_factor_info = two_factor_info or {}

