"""Exception hierarchy for SubTerminator CLI."""


class SubTerminatorError(Exception):
    """Base exception for all SubTerminator errors."""


class TransientError(SubTerminatorError):
    """Retry-able errors such as network timeouts or temporary failures."""


class PermanentError(SubTerminatorError):
    """Non-retry-able errors that require configuration or code changes."""


class ConfigurationError(PermanentError):
    """Invalid or missing configuration."""


class ServiceError(PermanentError):
    """Service-specific errors from third-party services."""


class HumanInterventionRequired(SubTerminatorError):  # noqa: N818
    """Flow requires human input to proceed."""


class UserAborted(SubTerminatorError):  # noqa: N818
    """User chose to abort the operation."""


class ElementNotFound(TransientError):  # noqa: N818
    """Element not found in page, may succeed on retry."""


class NavigationError(TransientError):
    """Page navigation failed, may succeed on retry."""


class StateDetectionError(TransientError):
    """Could not detect page state, may succeed on retry."""
