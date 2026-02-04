"""Unit tests for core protocols and data types.

Tests cover:
- State enum values and behavior
- AIInterpretation dataclass validation and defaults
- CancellationResult dataclass validation
- Protocol interface compliance
"""

from pathlib import Path

import pytest

from subterminator.core.protocols import (
    AIInterpretation,
    AIInterpreterProtocol,
    BrowserProtocol,
    CancellationResult,
    ServiceConfigProtocol,
    ServiceProtocol,
    State,
)


class TestState:
    """Tests for the State enum."""

    def test_all_states_exist(self) -> None:
        """All required states should be defined."""
        expected_states = [
            "START",
            "LOGIN_REQUIRED",
            "ACCOUNT_ACTIVE",
            "ACCOUNT_CANCELLED",
            "THIRD_PARTY_BILLING",
            "RETENTION_OFFER",
            "EXIT_SURVEY",
            "FINAL_CONFIRMATION",
            "COMPLETE",
            "ABORTED",
            "FAILED",
            "UNKNOWN",
        ]
        actual_states = [s.name for s in State]
        assert actual_states == expected_states

    def test_states_have_unique_values(self) -> None:
        """Each state should have a unique value."""
        values = [s.value for s in State]
        assert len(values) == len(set(values))

    def test_state_comparison(self) -> None:
        """States should be comparable."""
        assert State.START == State.START
        assert State.START != State.COMPLETE

    def test_state_is_hashable(self) -> None:
        """States should be usable as dictionary keys."""
        state_dict: dict[State, str] = {
            State.START: "beginning",
            State.COMPLETE: "done",
        }
        assert state_dict[State.START] == "beginning"


class TestAIInterpretation:
    """Tests for the AIInterpretation dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Should create with required fields only."""
        interpretation = AIInterpretation(
            state=State.LOGIN_REQUIRED,
            confidence=0.95,
            reasoning="Login form detected",
        )
        assert interpretation.state == State.LOGIN_REQUIRED
        assert interpretation.confidence == 0.95
        assert interpretation.reasoning == "Login form detected"
        assert interpretation.actions == []

    def test_create_with_all_fields(self) -> None:
        """Should create with all fields including actions."""
        actions = [
            {"action": "click", "selector": "#login-btn"},
            {"action": "fill", "selector": "#email", "value": "test@example.com"},
        ]
        interpretation = AIInterpretation(
            state=State.ACCOUNT_ACTIVE,
            confidence=0.85,
            reasoning="Account page with cancel option",
            actions=actions,
        )
        assert interpretation.state == State.ACCOUNT_ACTIVE
        assert interpretation.confidence == 0.85
        assert len(interpretation.actions) == 2
        assert interpretation.actions[0]["action"] == "click"

    def test_confidence_lower_bound(self) -> None:
        """Confidence at 0.0 should be valid."""
        interpretation = AIInterpretation(
            state=State.UNKNOWN,
            confidence=0.0,
            reasoning="Cannot determine state",
        )
        assert interpretation.confidence == 0.0

    def test_confidence_upper_bound(self) -> None:
        """Confidence at 1.0 should be valid."""
        interpretation = AIInterpretation(
            state=State.COMPLETE,
            confidence=1.0,
            reasoning="Confirmation message visible",
        )
        assert interpretation.confidence == 1.0

    def test_confidence_below_zero_raises_error(self) -> None:
        """Confidence below 0.0 should raise ValueError."""
        with pytest.raises(ValueError, match="confidence must be between"):
            AIInterpretation(
                state=State.UNKNOWN,
                confidence=-0.1,
                reasoning="Invalid",
            )

    def test_confidence_above_one_raises_error(self) -> None:
        """Confidence above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="confidence must be between"):
            AIInterpretation(
                state=State.UNKNOWN,
                confidence=1.1,
                reasoning="Invalid",
            )

    def test_actions_default_is_empty_list(self) -> None:
        """Actions should default to an empty list, not shared reference."""
        interp1 = AIInterpretation(
            state=State.START,
            confidence=0.5,
            reasoning="Test",
        )
        interp2 = AIInterpretation(
            state=State.START,
            confidence=0.5,
            reasoning="Test",
        )
        interp1.actions.append({"action": "click"})
        assert len(interp2.actions) == 0  # Ensure independent lists


class TestCancellationResult:
    """Tests for the CancellationResult dataclass."""

    def test_create_success_result(self) -> None:
        """Should create a successful result."""
        result = CancellationResult(
            success=True,
            state=State.COMPLETE,
            message="Cancellation completed successfully",
            session_dir=Path("/tmp/session_123"),
            effective_date="2026-03-01",
        )
        assert result.success is True
        assert result.state == State.COMPLETE
        assert result.message == "Cancellation completed successfully"
        assert result.session_dir == Path("/tmp/session_123")
        assert result.effective_date == "2026-03-01"

    def test_create_failure_result(self) -> None:
        """Should create a failure result."""
        result = CancellationResult(
            success=False,
            state=State.FAILED,
            message="Network timeout",
            session_dir=Path("/tmp/session_456"),
        )
        assert result.success is False
        assert result.state == State.FAILED
        assert result.message == "Network timeout"
        assert result.effective_date is None

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields should default to None."""
        result = CancellationResult(
            success=False,
            state=State.ABORTED,
            message="User aborted",
        )
        assert result.session_dir is None
        assert result.effective_date is None

    def test_already_cancelled_result(self) -> None:
        """Should handle already cancelled case."""
        result = CancellationResult(
            success=True,
            state=State.ACCOUNT_CANCELLED,
            message="Subscription already cancelled",
        )
        assert result.success is True
        assert result.state == State.ACCOUNT_CANCELLED


class TestBrowserProtocol:
    """Tests for BrowserProtocol compliance."""

    def test_protocol_is_structural(self) -> None:
        """BrowserProtocol should work as structural typing."""

        class MockBrowser:
            """Mock implementation of BrowserProtocol."""

            async def launch(self) -> None:
                pass

            async def navigate(self, url: str, timeout: int = 30000) -> None:
                pass

            async def click(
                self,
                selector: str | list[str],
                fallback_role: tuple[str, str] | None = None,
                timeout: int = 5000,
            ) -> None:
                pass

            async def fill(self, selector: str, value: str) -> None:
                pass

            async def select_option(
                self, selector: str, value: str | None = None
            ) -> None:
                pass

            async def screenshot(self, path: str | None = None) -> bytes:
                return b"fake_image_data"

            async def html(self) -> str:
                return "<html></html>"

            async def url(self) -> str:
                return "https://example.com"

            async def text_content(self) -> str:
                return "Page content"

            async def close(self) -> None:
                pass

            @property
            def is_cdp_connection(self) -> bool:
                return False

        # This should pass type checking - MockBrowser satisfies BrowserProtocol
        browser: BrowserProtocol = MockBrowser()
        assert isinstance(browser, MockBrowser)

    async def test_click_accepts_fallback_role_parameter(self) -> None:
        """BrowserProtocol.click() should accept fallback_role parameter."""

        class MockBrowserWithFallbackRole:
            """Mock browser that uses fallback_role."""

            last_click_fallback_role: tuple[str, str] | None = None

            async def launch(self) -> None:
                pass

            async def navigate(self, url: str, timeout: int = 30000) -> None:
                pass

            async def click(
                self,
                selector: str | list[str],
                fallback_role: tuple[str, str] | None = None,
                timeout: int = 5000,
            ) -> None:
                self.last_click_fallback_role = fallback_role

            async def fill(self, selector: str, value: str) -> None:
                pass

            async def select_option(
                self, selector: str, value: str | None = None
            ) -> None:
                pass

            async def screenshot(self, path: str | None = None) -> bytes:
                return b""

            async def html(self) -> str:
                return ""

            async def url(self) -> str:
                return ""

            async def text_content(self) -> str:
                return ""

            async def close(self) -> None:
                pass

            @property
            def is_cdp_connection(self) -> bool:
                return False

        browser: BrowserProtocol = MockBrowserWithFallbackRole()
        await browser.click("#btn", fallback_role=("button", "Submit"))
        assert browser.last_click_fallback_role == ("button", "Submit")

    async def test_click_accepts_timeout_parameter(self) -> None:
        """BrowserProtocol.click() should accept timeout parameter."""

        class MockBrowserWithTimeout:
            """Mock browser that uses timeout."""

            last_click_timeout: int = 0

            async def launch(self) -> None:
                pass

            async def navigate(self, url: str, timeout: int = 30000) -> None:
                pass

            async def click(
                self,
                selector: str | list[str],
                fallback_role: tuple[str, str] | None = None,
                timeout: int = 5000,
            ) -> None:
                self.last_click_timeout = timeout

            async def fill(self, selector: str, value: str) -> None:
                pass

            async def select_option(
                self, selector: str, value: str | None = None
            ) -> None:
                pass

            async def screenshot(self, path: str | None = None) -> bytes:
                return b""

            async def html(self) -> str:
                return ""

            async def url(self) -> str:
                return ""

            async def text_content(self) -> str:
                return ""

            async def close(self) -> None:
                pass

            @property
            def is_cdp_connection(self) -> bool:
                return False

        browser: BrowserProtocol = MockBrowserWithTimeout()
        await browser.click("#btn", timeout=10000)
        assert browser.last_click_timeout == 10000

    def test_is_cdp_connection_property(self) -> None:
        """BrowserProtocol should have is_cdp_connection property."""

        class MockCDPBrowser:
            """Mock browser connected via CDP."""

            async def launch(self) -> None:
                pass

            async def navigate(self, url: str, timeout: int = 30000) -> None:
                pass

            async def click(
                self,
                selector: str | list[str],
                fallback_role: tuple[str, str] | None = None,
                timeout: int = 5000,
            ) -> None:
                pass

            async def fill(self, selector: str, value: str) -> None:
                pass

            async def select_option(
                self, selector: str, value: str | None = None
            ) -> None:
                pass

            async def screenshot(self, path: str | None = None) -> bytes:
                return b""

            async def html(self) -> str:
                return ""

            async def url(self) -> str:
                return ""

            async def text_content(self) -> str:
                return ""

            async def close(self) -> None:
                pass

            @property
            def is_cdp_connection(self) -> bool:
                return True

        class MockManagedBrowser:
            """Mock browser not connected via CDP."""

            async def launch(self) -> None:
                pass

            async def navigate(self, url: str, timeout: int = 30000) -> None:
                pass

            async def click(
                self,
                selector: str | list[str],
                fallback_role: tuple[str, str] | None = None,
                timeout: int = 5000,
            ) -> None:
                pass

            async def fill(self, selector: str, value: str) -> None:
                pass

            async def select_option(
                self, selector: str, value: str | None = None
            ) -> None:
                pass

            async def screenshot(self, path: str | None = None) -> bytes:
                return b""

            async def html(self) -> str:
                return ""

            async def url(self) -> str:
                return ""

            async def text_content(self) -> str:
                return ""

            async def close(self) -> None:
                pass

            @property
            def is_cdp_connection(self) -> bool:
                return False

        cdp_browser: BrowserProtocol = MockCDPBrowser()
        managed_browser: BrowserProtocol = MockManagedBrowser()

        assert cdp_browser.is_cdp_connection is True
        assert managed_browser.is_cdp_connection is False


class TestAIInterpreterProtocol:
    """Tests for AIInterpreterProtocol compliance."""

    def test_protocol_is_structural(self) -> None:
        """AIInterpreterProtocol should work as structural typing."""

        class MockInterpreter:
            """Mock implementation of AIInterpreterProtocol."""

            def interpret(self, screenshot: bytes) -> AIInterpretation:
                return AIInterpretation(
                    state=State.UNKNOWN,
                    confidence=0.5,
                    reasoning="Mock interpretation",
                )

        interpreter: AIInterpreterProtocol = MockInterpreter()
        result = interpreter.interpret(b"fake_screenshot")
        assert result.state == State.UNKNOWN


class TestServiceConfigProtocol:
    """Tests for ServiceConfigProtocol compliance."""

    def test_service_config_protocol_has_name_property(self) -> None:
        """ServiceConfigProtocol should have name property."""

        class MockConfig:
            """Mock implementation of ServiceConfigProtocol."""

            @property
            def name(self) -> str:
                return "test_service"

        config: ServiceConfigProtocol = MockConfig()
        assert config.name == "test_service"


class TestServiceProtocol:
    """Tests for ServiceProtocol compliance."""

    def test_protocol_is_structural(self) -> None:
        """ServiceProtocol should work as structural typing."""

        class MockConfig:
            """Mock config that satisfies ServiceConfigProtocol."""

            @property
            def name(self) -> str:
                return "test_service"

        class MockService:
            """Mock implementation of ServiceProtocol."""

            @property
            def config(self) -> ServiceConfigProtocol:
                return MockConfig()

            @property
            def entry_url(self) -> str:
                return "https://example.com/account"

            @property
            def selectors(self) -> dict[str, str | list[str]]:
                return {
                    "cancel_button": "#cancel-btn",
                    "confirm_buttons": ["#confirm", "#yes-confirm"],
                }

            @property
            def service_id(self) -> str:
                return "mock_service"

        service: ServiceProtocol = MockService()
        assert service.entry_url == "https://example.com/account"
        assert service.config.name == "test_service"
        assert "cancel_button" in service.selectors
        assert service.service_id == "mock_service"

    def test_service_id_property(self) -> None:
        """ServiceProtocol should have service_id property."""

        class MockConfig:
            """Mock config that satisfies ServiceConfigProtocol."""

            @property
            def name(self) -> str:
                return "My Service"

        class MockService:
            """Mock implementation with service_id."""

            @property
            def config(self) -> ServiceConfigProtocol:
                return MockConfig()

            @property
            def entry_url(self) -> str:
                return "https://example.com"

            @property
            def selectors(self) -> dict[str, str | list[str]]:
                return {}

            @property
            def service_id(self) -> str:
                return "my_service_id"

        service: ServiceProtocol = MockService()
        assert service.service_id == "my_service_id"

    def test_netflix_service_satisfies_updated_protocol(self) -> None:
        """NetflixService should satisfy the updated ServiceProtocol."""
        from subterminator.services.netflix import NetflixService

        service = NetflixService()
        # Verify it has all required properties
        assert hasattr(service, "config")
        assert hasattr(service, "entry_url")
        assert hasattr(service, "selectors")
        assert hasattr(service, "service_id")

        # Verify the config has name property
        assert hasattr(service.config, "name")
        assert service.config.name == "Netflix"

        # Verify service_id returns a string
        assert isinstance(service.service_id, str)
        assert service.service_id == "netflix"


class TestModuleExports:
    """Tests for module exports from core package."""

    def test_exports_from_core_init(self) -> None:
        """All types should be importable from subterminator.core."""
        from subterminator.core import (
            AIInterpretation,
            AIInterpreterProtocol,
            BrowserProtocol,
            CancellationResult,
            ServiceProtocol,
            State,
        )

        # Verify they're the correct types
        assert State.START is not None
        assert AIInterpretation.__name__ == "AIInterpretation"
        assert CancellationResult.__name__ == "CancellationResult"
        assert BrowserProtocol.__name__ == "BrowserProtocol"
        assert AIInterpreterProtocol.__name__ == "AIInterpreterProtocol"
        assert ServiceProtocol.__name__ == "ServiceProtocol"
