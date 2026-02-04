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


class CDPConnectionError(PermanentError):
    """Cannot connect to Chrome via CDP (Chrome DevTools Protocol).

    This error occurs when the browser automation cannot establish a
    connection to Chrome's debugging port.
    """

    def __init__(self, url: str) -> None:
        """Initialize CDPConnectionError with the target URL.

        Args:
            url: The CDP URL that could not be connected to.
        """
        self.url = url
        super().__init__(
            f"Cannot connect to Chrome at {url}. "
            "Is Chrome running with --remote-debugging-port?"
        )


class ProfileLoadError(PermanentError):
    """Failed to load a browser profile from disk.

    This error occurs when the browser automation cannot load
    a user profile from the specified path.
    """

    def __init__(self, path: str) -> None:
        """Initialize ProfileLoadError with the profile path.

        Args:
            path: The file path to the profile that could not be loaded.
        """
        self.path = path
        super().__init__(f"Failed to load browser profile from {path}")
