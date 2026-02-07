"""Unit tests for Claude-DA exception hierarchy.

Verifies inheritance chain, status_code/error_code attributes,
and str() behavior for all custom exceptions.
"""

import pytest

from claude_da.exceptions import (
    AgentTimeoutError,
    ClaudeDAError,
    ConfigurationError,
    DatabaseUnavailableError,
    InputValidationError,
    RateLimitError,
)


class TestExceptionInheritance:
    """All custom exceptions descend from ClaudeDAError."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ConfigurationError,
            InputValidationError,
            AgentTimeoutError,
            RateLimitError,
            DatabaseUnavailableError,
        ],
    )
    def test_subclass_of_claude_da_error(self, exc_cls: type[ClaudeDAError]) -> None:
        assert issubclass(exc_cls, ClaudeDAError)

    def test_claude_da_error_is_exception(self) -> None:
        assert issubclass(ClaudeDAError, Exception)


class TestStatusAndErrorCodes:
    """Exceptions that represent HTTP-like failures carry status_code and error_code."""

    def test_input_validation_error_codes(self) -> None:
        err = InputValidationError("too long")
        assert err.status_code == 400
        assert err.error_code == "input_too_long"

    def test_agent_timeout_error_codes(self) -> None:
        err = AgentTimeoutError("timed out")
        assert err.status_code == 504
        assert err.error_code == "agent_timeout"

    def test_rate_limit_error_codes(self) -> None:
        err = RateLimitError("slow down")
        assert err.status_code == 429
        assert err.error_code == "rate_limited"

    def test_database_unavailable_error_codes(self) -> None:
        err = DatabaseUnavailableError("cannot connect")
        assert err.status_code == 503
        assert err.error_code == "database_unavailable"


class TestStrRepresentation:
    """str() on every exception should return the message."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ClaudeDAError,
            ConfigurationError,
            InputValidationError,
            AgentTimeoutError,
            RateLimitError,
            DatabaseUnavailableError,
        ],
    )
    def test_str_contains_message(self, exc_cls: type[ClaudeDAError]) -> None:
        msg = "something went wrong"
        err = exc_cls(msg)
        assert str(err) == msg

    def test_base_error_no_message(self) -> None:
        err = ClaudeDAError()
        assert str(err) == ""


class TestRaiseAndCatch:
    """Exceptions can be raised and caught at the base class level."""

    def test_catch_input_validation_as_base(self) -> None:
        with pytest.raises(ClaudeDAError):
            raise InputValidationError("bad input")

    def test_catch_configuration_as_base(self) -> None:
        with pytest.raises(ClaudeDAError):
            raise ConfigurationError("missing key")

    def test_catch_agent_timeout_as_base(self) -> None:
        with pytest.raises(ClaudeDAError):
            raise AgentTimeoutError("took too long")
