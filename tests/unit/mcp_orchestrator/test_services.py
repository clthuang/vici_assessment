"""Tests for MCP orchestrator service configurations."""

import pytest

from subterminator.mcp_orchestrator.exceptions import ServiceNotFoundError
from subterminator.mcp_orchestrator.services.base import ServiceConfig
from subterminator.mcp_orchestrator.services.registry import ServiceRegistry
from subterminator.mcp_orchestrator.types import NormalizedSnapshot, ToolCall


class TestServiceConfig:
    """Tests for ServiceConfig dataclass."""

    def test_create_minimal_config(self):
        """ServiceConfig can be created with required fields only."""
        config = ServiceConfig(
            name="test",
            initial_url="https://example.com",
            goal_template="Cancel {service} subscription",
        )
        assert config.name == "test"
        assert config.initial_url == "https://example.com"
        assert config.checkpoint_conditions == []
        assert config.success_indicators == []
        assert config.system_prompt_addition == ""

    def test_create_full_config(self):
        """ServiceConfig can be created with all fields."""
        def checkpoint(tool: ToolCall, snap: NormalizedSnapshot) -> bool:
            return True

        def success(snap: NormalizedSnapshot) -> bool:
            return True

        config = ServiceConfig(
            name="test",
            initial_url="https://example.com",
            goal_template="Cancel {service}",
            checkpoint_conditions=[checkpoint],
            success_indicators=[success],
            failure_indicators=[success],
            system_prompt_addition="Extra instructions",
            auth_edge_case_detectors=[success],
        )
        assert len(config.checkpoint_conditions) == 1
        assert len(config.success_indicators) == 1
        assert config.system_prompt_addition == "Extra instructions"


class TestServiceRegistry:
    """Tests for ServiceRegistry."""

    def test_register_and_get(self):
        """Registry can register and retrieve configs."""
        registry = ServiceRegistry()
        config = ServiceConfig(
            name="myservice",
            initial_url="https://myservice.com",
            goal_template="Test goal",
        )
        registry.register(config)

        result = registry.get("myservice")
        assert result is config

    def test_get_unknown_raises(self):
        """get() raises ServiceNotFoundError for unknown service."""
        registry = ServiceRegistry()
        with pytest.raises(ServiceNotFoundError) as exc_info:
            registry.get("unknown")
        assert "unknown" in str(exc_info.value)
        assert "Available services: none" in str(exc_info.value)

    def test_get_unknown_shows_available(self):
        """Error message shows available services."""
        registry = ServiceRegistry()
        registry.register(ServiceConfig(
            name="svc1", initial_url="u", goal_template="g",
        ))
        registry.register(ServiceConfig(
            name="svc2", initial_url="u", goal_template="g",
        ))

        with pytest.raises(ServiceNotFoundError) as exc_info:
            registry.get("unknown")
        assert "svc1" in str(exc_info.value)
        assert "svc2" in str(exc_info.value)

    def test_list_services(self):
        """list_services() returns sorted service names."""
        registry = ServiceRegistry()
        registry.register(ServiceConfig(
            name="zebra", initial_url="u", goal_template="g",
        ))
        registry.register(ServiceConfig(
            name="alpha", initial_url="u", goal_template="g",
        ))

        result = registry.list_services()
        assert result == ["alpha", "zebra"]

    def test_list_services_empty(self):
        """list_services() returns empty list when empty."""
        registry = ServiceRegistry()
        assert registry.list_services() == []


class TestNetflixConfig:
    """Tests for Netflix service configuration."""

    @pytest.fixture
    def netflix_config(self):
        """Get Netflix config from default registry."""
        # Import here to trigger registration
        from subterminator.mcp_orchestrator.services.registry import default_registry
        return default_registry.get("netflix")

    def test_netflix_registered(self, netflix_config):
        """Netflix config is registered in default registry."""
        assert netflix_config.name == "netflix"
        assert "netflix.com" in netflix_config.initial_url

    def test_netflix_has_checkpoint_conditions(self, netflix_config):
        """Netflix config has checkpoint conditions."""
        # Only payment page protection - cancel is reversible so minimal checkpoints
        assert len(netflix_config.checkpoint_conditions) >= 1

    def test_netflix_has_success_indicators(self, netflix_config):
        """Netflix config has success indicators."""
        assert len(netflix_config.success_indicators) >= 2

    def test_netflix_has_failure_indicators(self, netflix_config):
        """Netflix config has failure indicators."""
        assert len(netflix_config.failure_indicators) >= 2


class TestNetflixCheckpointPredicates:
    """Tests for Netflix checkpoint predicates."""

    @pytest.fixture
    def predicates(self):
        """Get Netflix checkpoint predicates."""
        from subterminator.mcp_orchestrator.services.netflix import (
            is_destructive_click,
            is_final_cancel_page,
            is_payment_page,
        )
        return {
            "destructive": is_destructive_click,
            "final_cancel": is_final_cancel_page,
            "payment": is_payment_page,
        }

    def test_destructive_click_triggers(self, predicates):
        """is_destructive_click triggers on finality keywords."""
        tool = ToolCall(
            id="1", name="browser_click",
            args={"element": "Finish Cancellation"},
        )
        snap = NormalizedSnapshot(
            url="/cancel", title="Cancel", content="page content",
        )
        assert predicates["destructive"](tool, snap) is True

    def test_destructive_click_ignores_non_click(self, predicates):
        """is_destructive_click ignores non-click tools."""
        tool = ToolCall(id="1", name="browser_snapshot", args={})
        snap = NormalizedSnapshot(url="/cancel", title="Cancel", content="finish")
        assert predicates["destructive"](tool, snap) is False

    def test_destructive_click_ignores_safe_elements(self, predicates):
        """is_destructive_click ignores safe element names."""
        tool = ToolCall(id="1", name="browser_click", args={"element": "Next"})
        snap = NormalizedSnapshot(url="/cancel", title="Cancel", content="page content")
        assert predicates["destructive"](tool, snap) is False

    def test_final_cancel_page_triggers(self, predicates):
        """is_final_cancel_page triggers when both finish and cancel present."""
        tool = ToolCall(id="1", name="browser_click", args={})
        snap = NormalizedSnapshot(
            url="/cancel",
            title="Cancel",
            content="Click Finish to cancel your membership"
        )
        assert predicates["final_cancel"](tool, snap) is True

    def test_final_cancel_page_requires_both_keywords(self, predicates):
        """is_final_cancel_page requires both keywords."""
        tool = ToolCall(id="1", name="browser_click", args={})
        # Only "finish" without "cancel"
        snap = NormalizedSnapshot(url="/finish", title="Done", content="finish setup")
        assert predicates["final_cancel"](tool, snap) is False

    def test_payment_page_triggers_on_url(self, predicates):
        """is_payment_page triggers on payment in URL."""
        tool = ToolCall(id="1", name="browser_click", args={})
        snap = NormalizedSnapshot(
            url="/payment-method", title="Payment", content="card",
        )
        assert predicates["payment"](tool, snap) is True

    def test_payment_page_triggers_on_content(self, predicates):
        """is_payment_page triggers on billing in content."""
        tool = ToolCall(id="1", name="browser_click", args={})
        snap = NormalizedSnapshot(
            url="/settings", title="Settings",
            content="billing info",
        )
        assert predicates["payment"](tool, snap) is True


class TestNetflixSuccessIndicators:
    """Tests for Netflix success indicators."""

    @pytest.fixture
    def indicators(self):
        """Get Netflix success indicators."""
        from subterminator.mcp_orchestrator.services.netflix import (
            has_already_cancelled,
            has_cancellation_confirmed,
            has_membership_ended,
            has_restart_option,
        )
        return {
            "confirmed": has_cancellation_confirmed,
            "ended": has_membership_ended,
            "restart": has_restart_option,
            "already_cancelled": has_already_cancelled,
        }

    def test_cancellation_confirmed_triggers(self, indicators):
        """has_cancellation_confirmed detects confirmation."""
        snap = NormalizedSnapshot(
            url="/done",
            title="Done",
            content="Your cancellation confirmed. Thank you."
        )
        assert indicators["confirmed"](snap) is True

    def test_membership_ended_triggers(self, indicators):
        """has_membership_ended detects end message."""
        snap = NormalizedSnapshot(
            url="/done",
            title="Done",
            content="Your membership will end on December 31"
        )
        assert indicators["ended"](snap) is True

    def test_restart_option_triggers(self, indicators):
        """has_restart_option detects restart membership link."""
        snap = NormalizedSnapshot(
            url="/account",
            title="Account",
            content="Click here to restart membership"
        )
        assert indicators["restart"](snap) is True

    def test_already_cancelled_triggers(self, indicators):
        """has_already_cancelled detects already cancelled state."""
        snap = NormalizedSnapshot(
            url="/account",
            title="Account",
            content="You cancelled your membership on January 15"
        )
        assert indicators["already_cancelled"](snap) is True

    def test_already_cancelled_variant(self, indicators):
        """has_already_cancelled detects various cancelled message variants."""
        snap = NormalizedSnapshot(
            url="/account",
            title="Account",
            content="Your membership is cancelled. Restart anytime."
        )
        assert indicators["already_cancelled"](snap) is True


class TestNetflixFailureIndicators:
    """Tests for Netflix failure indicators."""

    @pytest.fixture
    def indicators(self):
        """Get Netflix failure indicators."""
        from subterminator.mcp_orchestrator.services.netflix import (
            has_error_message,
            has_session_expired,
            has_try_again,
        )
        return {
            "error": has_error_message,
            "try_again": has_try_again,
            "expired": has_session_expired,
        }

    def test_error_message_triggers(self, indicators):
        """has_error_message detects error."""
        snap = NormalizedSnapshot(
            url="/cancel",
            title="Error",
            content="Something went wrong. Please contact support."
        )
        assert indicators["error"](snap) is True

    def test_try_again_triggers(self, indicators):
        """has_try_again detects retry prompt."""
        snap = NormalizedSnapshot(
            url="/cancel",
            title="Error",
            content="Unable to process. Please try again later."
        )
        assert indicators["try_again"](snap) is True

    def test_session_expired_triggers(self, indicators):
        """has_session_expired detects session expiration."""
        snap = NormalizedSnapshot(
            url="/cancel",
            title="Session",
            content="Your session has expired. Please sign in again."
        )
        assert indicators["expired"](snap) is True


class TestNetflixAuthEdgeCases:
    """Tests for Netflix auth edge case detectors."""

    @pytest.fixture
    def detectors(self):
        """Get Netflix auth edge case detectors."""
        from subterminator.mcp_orchestrator.services.netflix import (
            is_captcha_page,
            is_login_page,
            is_mfa_page,
        )
        return {
            "login": is_login_page,
            "captcha": is_captcha_page,
            "mfa": is_mfa_page,
        }

    def test_login_page_detected_by_url(self, detectors):
        """is_login_page detects login URL."""
        snap = NormalizedSnapshot(
            url="https://www.netflix.com/login",
            title="Sign In",
            content="Email and password"
        )
        assert detectors["login"](snap) is True

    def test_captcha_page_detected(self, detectors):
        """is_captcha_page detects CAPTCHA."""
        snap = NormalizedSnapshot(
            url="/verify",
            title="Verify",
            content="Please verify you're human"
        )
        assert detectors["captcha"](snap) is True

    def test_mfa_page_detected(self, detectors):
        """is_mfa_page detects MFA."""
        snap = NormalizedSnapshot(
            url="/verify",
            title="Verify",
            content="Enter the verification code from your authenticator app"
        )
        assert detectors["mfa"](snap) is True
