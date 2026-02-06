"""Tests for SubTerminator exception hierarchy."""

import pytest

from subterminator.utils.exceptions import (
    CDPConnectionError,
    ConfigurationError,
    ElementNotFound,
    HumanInterventionRequired,
    NavigationError,
    PermanentError,
    ProfileLoadError,
    ServiceError,
    StateDetectionError,
    SubTerminatorError,
    TransientError,
    UserAborted,
)


class TestExceptionHierarchy:
    """Test the exception class hierarchy."""

    def test_subterminator_error_is_base_exception(self):
        """SubTerminatorError should inherit from Exception."""
        assert issubclass(SubTerminatorError, Exception)

    def test_transient_error_inherits_from_base(self):
        """TransientError should inherit from SubTerminatorError."""
        assert issubclass(TransientError, SubTerminatorError)

    def test_permanent_error_inherits_from_base(self):
        """PermanentError should inherit from SubTerminatorError."""
        assert issubclass(PermanentError, SubTerminatorError)

    def test_configuration_error_inherits_from_permanent(self):
        """ConfigurationError should inherit from PermanentError."""
        assert issubclass(ConfigurationError, PermanentError)
        assert issubclass(ConfigurationError, SubTerminatorError)

    def test_service_error_inherits_from_permanent(self):
        """ServiceError should inherit from PermanentError."""
        assert issubclass(ServiceError, PermanentError)
        assert issubclass(ServiceError, SubTerminatorError)

    def test_human_intervention_required_inherits_from_base(self):
        """HumanInterventionRequired should inherit from SubTerminatorError."""
        assert issubclass(HumanInterventionRequired, SubTerminatorError)

    def test_user_aborted_inherits_from_base(self):
        """UserAborted should inherit from SubTerminatorError."""
        assert issubclass(UserAborted, SubTerminatorError)

    def test_element_not_found_inherits_from_transient(self):
        """ElementNotFound should inherit from TransientError."""
        assert issubclass(ElementNotFound, TransientError)
        assert issubclass(ElementNotFound, SubTerminatorError)

    def test_navigation_error_inherits_from_transient(self):
        """NavigationError should inherit from TransientError."""
        assert issubclass(NavigationError, TransientError)
        assert issubclass(NavigationError, SubTerminatorError)

    def test_state_detection_error_inherits_from_transient(self):
        """StateDetectionError should inherit from TransientError."""
        assert issubclass(StateDetectionError, TransientError)
        assert issubclass(StateDetectionError, SubTerminatorError)

    def test_cdp_connection_error_inherits_from_permanent(self):
        """CDPConnectionError should inherit from PermanentError."""
        assert issubclass(CDPConnectionError, PermanentError)
        assert issubclass(CDPConnectionError, SubTerminatorError)

    def test_profile_load_error_inherits_from_permanent(self):
        """ProfileLoadError should inherit from PermanentError."""
        assert issubclass(ProfileLoadError, PermanentError)
        assert issubclass(ProfileLoadError, SubTerminatorError)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught correctly."""

    def test_raise_subterminator_error(self):
        """Should be able to raise and catch SubTerminatorError."""
        with pytest.raises(SubTerminatorError) as exc_info:
            raise SubTerminatorError("test error")
        assert str(exc_info.value) == "test error"

    def test_catch_transient_as_base(self):
        """TransientError should be catchable as SubTerminatorError."""
        with pytest.raises(SubTerminatorError):
            raise TransientError("transient")

    def test_catch_permanent_as_base(self):
        """PermanentError should be catchable as SubTerminatorError."""
        with pytest.raises(SubTerminatorError):
            raise PermanentError("permanent")

    def test_catch_element_not_found_as_transient(self):
        """ElementNotFound should be catchable as TransientError."""
        with pytest.raises(TransientError):
            raise ElementNotFound("element not found")

    def test_catch_configuration_error_as_permanent(self):
        """ConfigurationError should be catchable as PermanentError."""
        with pytest.raises(PermanentError):
            raise ConfigurationError("bad config")

    def test_transient_not_catchable_as_permanent(self):
        """TransientError should NOT be catchable as PermanentError."""
        with pytest.raises(TransientError):
            try:
                raise ElementNotFound("element")
            except PermanentError:
                pytest.fail("TransientError should not be caught as PermanentError")
            raise


class TestCDPConnectionError:
    """Tests for CDPConnectionError."""

    def test_message_format(self):
        """CDPConnectionError should format message with URL."""
        url = "http://localhost:9222"
        error = CDPConnectionError(url)
        assert url in str(error)
        assert "Chrome" in str(error)
        assert "remote-debugging-port" in str(error)

    def test_url_attribute(self):
        """CDPConnectionError should store the URL as an attribute."""
        url = "http://localhost:9222"
        error = CDPConnectionError(url)
        assert error.url == url

    def test_full_message_content(self):
        """CDPConnectionError should have the expected full message."""
        url = "http://127.0.0.1:9333"
        error = CDPConnectionError(url)
        expected_msg = (
            f"Cannot connect to Chrome at {url}. "
            "Is Chrome running with --remote-debugging-port?"
        )
        assert str(error) == expected_msg


class TestProfileLoadError:
    """Tests for ProfileLoadError."""

    def test_message_format(self):
        """ProfileLoadError should format message with path."""
        path = "/Users/test/.config/chrome/profile"
        error = ProfileLoadError(path)
        assert path in str(error)
        assert "profile" in str(error).lower()

    def test_path_attribute(self):
        """ProfileLoadError should store the path as an attribute."""
        path = "/Users/test/.config/chrome/profile"
        error = ProfileLoadError(path)
        assert error.path == path

    def test_full_message_content(self):
        """ProfileLoadError should have the expected full message."""
        path = "/home/user/.chrome/Default"
        error = ProfileLoadError(path)
        expected_msg = f"Failed to load browser profile from {path}"
        assert str(error) == expected_msg


class TestExceptionDocstrings:
    """Test that all exceptions have docstrings."""

    def test_subterminator_error_has_docstring(self):
        """SubTerminatorError should have a docstring."""
        assert SubTerminatorError.__doc__ is not None
        assert "Base exception" in SubTerminatorError.__doc__

    def test_transient_error_has_docstring(self):
        """TransientError should have a docstring."""
        assert TransientError.__doc__ is not None
        assert "retry" in TransientError.__doc__.lower()

    def test_permanent_error_has_docstring(self):
        """PermanentError should have a docstring."""
        assert PermanentError.__doc__ is not None
        assert "retry" in PermanentError.__doc__.lower()

    def test_configuration_error_has_docstring(self):
        """ConfigurationError should have a docstring."""
        assert ConfigurationError.__doc__ is not None
        assert "configuration" in ConfigurationError.__doc__.lower()

    def test_service_error_has_docstring(self):
        """ServiceError should have a docstring."""
        assert ServiceError.__doc__ is not None
        assert "service" in ServiceError.__doc__.lower()

    def test_human_intervention_required_has_docstring(self):
        """HumanInterventionRequired should have a docstring."""
        assert HumanInterventionRequired.__doc__ is not None
        assert "human" in HumanInterventionRequired.__doc__.lower()

    def test_user_aborted_has_docstring(self):
        """UserAborted should have a docstring."""
        assert UserAborted.__doc__ is not None
        assert "abort" in UserAborted.__doc__.lower()

    def test_element_not_found_has_docstring(self):
        """ElementNotFound should have a docstring."""
        assert ElementNotFound.__doc__ is not None
        assert "element" in ElementNotFound.__doc__.lower()

    def test_navigation_error_has_docstring(self):
        """NavigationError should have a docstring."""
        assert NavigationError.__doc__ is not None
        assert "navigation" in NavigationError.__doc__.lower()

    def test_state_detection_error_has_docstring(self):
        """StateDetectionError should have a docstring."""
        assert StateDetectionError.__doc__ is not None
        assert "state" in StateDetectionError.__doc__.lower()

    def test_cdp_connection_error_has_docstring(self):
        """CDPConnectionError should have a docstring."""
        assert CDPConnectionError.__doc__ is not None
        doc_lower = CDPConnectionError.__doc__.lower()
        assert "cdp" in doc_lower or "chrome" in doc_lower

    def test_profile_load_error_has_docstring(self):
        """ProfileLoadError should have a docstring."""
        assert ProfileLoadError.__doc__ is not None
        assert "profile" in ProfileLoadError.__doc__.lower()


class TestModuleExports:
    """Test that exceptions are properly exported from the utils module."""

    def test_import_from_utils(self):
        """All exceptions should be importable from subterminator.utils."""
        from subterminator.utils import (
            CDPConnectionError,
            ConfigurationError,
            ElementNotFound,
            HumanInterventionRequired,
            NavigationError,
            PermanentError,
            ProfileLoadError,
            ServiceError,
            StateDetectionError,
            SubTerminatorError,
            TransientError,
            UserAborted,
        )

        # Just verify they imported successfully
        assert SubTerminatorError is not None
        assert TransientError is not None
        assert PermanentError is not None
        assert ConfigurationError is not None
        assert ServiceError is not None
        assert HumanInterventionRequired is not None
        assert UserAborted is not None
        assert ElementNotFound is not None
        assert NavigationError is not None
        assert StateDetectionError is not None
        assert CDPConnectionError is not None
        assert ProfileLoadError is not None
