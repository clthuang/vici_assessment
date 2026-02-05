"""Exception hierarchy for MCP (Model Context Protocol) browser control.

This module defines exception types that correspond to error codes used in
tool results. Each exception provides structured error information that can
be mapped to an ErrorCode when converting to ToolResult.
"""


class MCPError(Exception):
    """Base exception for MCP browser control.

    All MCP-specific exceptions inherit from this class to allow for
    broad exception handling when needed.
    """


class RefInvalidError(MCPError):
    """Element reference not found in current snapshot.

    This error occurs when a tool attempts to use an element reference
    (e.g., "@e7") that does not exist in the current snapshot. References
    are invalidated after any action that modifies the page state.

    Attributes:
        ref: The invalid element reference.
    """

    def __init__(self, ref: str) -> None:
        """Initialize RefInvalidError.

        Args:
            ref: The element reference that was not found.
        """
        self.ref = ref
        super().__init__(f"Element reference '{ref}' not found in current snapshot")


class ElementDisabledError(MCPError):
    """Element is disabled and cannot be interacted with.

    This error occurs when attempting to interact with an element that
    has the "disabled" state set.

    Attributes:
        ref: The element reference.
    """

    def __init__(self, ref: str) -> None:
        """Initialize ElementDisabledError.

        Args:
            ref: The element reference that is disabled.
        """
        self.ref = ref
        super().__init__(f"Element '{ref}' is disabled")


class ElementObscuredError(MCPError):
    """Element is covered by another element.

    This error occurs when attempting to click an element that is
    obscured by another element (e.g., a modal overlay).

    Attributes:
        ref: The target element reference.
        obscuring_element: Description of the obscuring element if known.
    """

    def __init__(self, ref: str, obscuring_element: str | None = None) -> None:
        """Initialize ElementObscuredError.

        Args:
            ref: The element reference that is obscured.
            obscuring_element: Optional description of what is obscuring the element.
        """
        self.ref = ref
        self.obscuring_element = obscuring_element
        msg = f"Element '{ref}' is obscured"
        if obscuring_element:
            msg += f" by '{obscuring_element}'"
        super().__init__(msg)


class MCPTimeoutError(MCPError):
    """Operation timed out.

    This error occurs when a browser operation does not complete within
    the specified timeout period.

    Note: Named MCPTimeoutError to avoid shadowing the built-in TimeoutError.

    Attributes:
        operation: Description of the operation that timed out.
        timeout_ms: Timeout duration in milliseconds.
    """

    def __init__(self, operation: str, timeout_ms: int) -> None:
        """Initialize MCPTimeoutError.

        Args:
            operation: Description of the operation that timed out.
            timeout_ms: Timeout duration in milliseconds.
        """
        self.operation = operation
        self.timeout_ms = timeout_ms
        super().__init__(f"Operation '{operation}' timed out after {timeout_ms}ms")


class InvalidParamsError(MCPError):
    """Invalid or missing parameters for tool call.

    This error occurs when a tool is called with invalid or missing
    required parameters.

    Attributes:
        tool: Name of the tool that received invalid params.
    """

    def __init__(self, tool: str, message: str) -> None:
        """Initialize InvalidParamsError.

        Args:
            tool: Name of the tool that received invalid parameters.
            message: Description of what is invalid about the parameters.
        """
        self.tool = tool
        super().__init__(f"Invalid params for '{tool}': {message}")
