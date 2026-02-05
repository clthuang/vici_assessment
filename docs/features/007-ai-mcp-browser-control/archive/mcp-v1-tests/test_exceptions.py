"""Tests for MCP exceptions.

This module tests the exception types defined in subterminator.mcp.exceptions,
verifying correct initialization, message formatting, and attributes.
"""

import pytest

from subterminator.mcp.exceptions import (
    ElementDisabledError,
    ElementObscuredError,
    InvalidParamsError,
    MCPError,
    MCPTimeoutError,
    RefInvalidError,
)


class TestMCPError:
    """Tests for MCPError base exception."""

    def test_basic_creation(self) -> None:
        """Test that MCPError can be created with a message."""
        error = MCPError("Something went wrong")

        assert str(error) == "Something went wrong"

    def test_is_base_exception(self) -> None:
        """Test that MCPError inherits from Exception."""
        error = MCPError("test")

        assert isinstance(error, Exception)


class TestRefInvalidError:
    """Tests for RefInvalidError."""

    def test_message_format(self) -> None:
        """Test that error message includes the ref."""
        error = RefInvalidError("@e99")

        assert "@e99" in str(error)
        assert "not found" in str(error)
        assert "current snapshot" in str(error)

    def test_ref_attribute(self) -> None:
        """Test that ref is stored as attribute."""
        error = RefInvalidError("@e42")

        assert error.ref == "@e42"

    def test_inherits_from_mcp_error(self) -> None:
        """Test that RefInvalidError inherits from MCPError."""
        error = RefInvalidError("@e0")

        assert isinstance(error, MCPError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that the exception can be raised and caught."""
        with pytest.raises(RefInvalidError) as exc_info:
            raise RefInvalidError("@e123")

        assert exc_info.value.ref == "@e123"


class TestElementDisabledError:
    """Tests for ElementDisabledError."""

    def test_message_format(self) -> None:
        """Test that error message includes the ref."""
        error = ElementDisabledError("@e5")

        assert "@e5" in str(error)
        assert "disabled" in str(error)

    def test_ref_attribute(self) -> None:
        """Test that ref is stored as attribute."""
        error = ElementDisabledError("@e10")

        assert error.ref == "@e10"

    def test_inherits_from_mcp_error(self) -> None:
        """Test that ElementDisabledError inherits from MCPError."""
        error = ElementDisabledError("@e0")

        assert isinstance(error, MCPError)


class TestElementObscuredError:
    """Tests for ElementObscuredError."""

    def test_message_without_obscuring_element(self) -> None:
        """Test error message when obscuring element is not known."""
        error = ElementObscuredError("@e7")

        assert "@e7" in str(error)
        assert "obscured" in str(error)

    def test_message_with_obscuring_element(self) -> None:
        """Test error message when obscuring element is known."""
        error = ElementObscuredError("@e7", obscuring_element="modal-overlay")

        assert "@e7" in str(error)
        assert "obscured" in str(error)
        assert "modal-overlay" in str(error)

    def test_ref_attribute(self) -> None:
        """Test that ref is stored as attribute."""
        error = ElementObscuredError("@e3")

        assert error.ref == "@e3"

    def test_obscuring_element_attribute(self) -> None:
        """Test that obscuring_element is stored as attribute."""
        error = ElementObscuredError("@e3", obscuring_element="popup")

        assert error.obscuring_element == "popup"

    def test_obscuring_element_none_by_default(self) -> None:
        """Test that obscuring_element is None when not provided."""
        error = ElementObscuredError("@e3")

        assert error.obscuring_element is None

    def test_inherits_from_mcp_error(self) -> None:
        """Test that ElementObscuredError inherits from MCPError."""
        error = ElementObscuredError("@e0")

        assert isinstance(error, MCPError)


class TestMCPTimeoutError:
    """Tests for MCPTimeoutError."""

    def test_message_format(self) -> None:
        """Test that error message includes operation and timeout."""
        error = MCPTimeoutError("click on @e5", 2000)

        assert "click on @e5" in str(error)
        assert "2000ms" in str(error)
        assert "timed out" in str(error)

    def test_operation_attribute(self) -> None:
        """Test that operation is stored as attribute."""
        error = MCPTimeoutError("fill input", 3000)

        assert error.operation == "fill input"

    def test_timeout_ms_attribute(self) -> None:
        """Test that timeout_ms is stored as attribute."""
        error = MCPTimeoutError("scroll", 5000)

        assert error.timeout_ms == 5000

    def test_inherits_from_mcp_error(self) -> None:
        """Test that MCPTimeoutError inherits from MCPError."""
        error = MCPTimeoutError("test", 1000)

        assert isinstance(error, MCPError)

    def test_does_not_shadow_builtin(self) -> None:
        """Test that MCPTimeoutError does not shadow built-in TimeoutError."""
        # Both should be importable and distinct
        from subterminator.mcp.exceptions import MCPTimeoutError as MTE

        assert MTE is not TimeoutError
        assert issubclass(MTE, MCPError)


class TestInvalidParamsError:
    """Tests for InvalidParamsError."""

    def test_message_format(self) -> None:
        """Test that error message includes tool and description."""
        error = InvalidParamsError("browser_click", "ref is required")

        assert "browser_click" in str(error)
        assert "ref is required" in str(error)
        assert "Invalid params" in str(error)

    def test_tool_attribute(self) -> None:
        """Test that tool is stored as attribute."""
        error = InvalidParamsError("browser_scroll", "either ref or direction required")

        assert error.tool == "browser_scroll"

    def test_inherits_from_mcp_error(self) -> None:
        """Test that InvalidParamsError inherits from MCPError."""
        error = InvalidParamsError("test", "test")

        assert isinstance(error, MCPError)

    def test_detailed_message(self) -> None:
        """Test error with detailed parameter validation message."""
        error = InvalidParamsError(
            "browser_fill",
            "value must be a non-empty string, got empty string"
        )

        assert "browser_fill" in str(error)
        assert "value must be a non-empty string" in str(error)
