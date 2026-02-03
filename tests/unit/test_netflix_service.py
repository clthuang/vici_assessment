"""Unit tests for Netflix service implementation."""

import pytest

from subterminator.services.netflix import (
    NetflixService,
    ServiceConfig,
    ServiceSelectors,
)


class TestServiceSelectors:
    """Tests for ServiceSelectors dataclass."""

    def test_selectors_initialization(self):
        """Test ServiceSelectors can be initialized with all fields."""
        selectors = ServiceSelectors(
            cancel_link=["selector1"],
            decline_offer=["selector2"],
            survey_option=["selector3"],
            survey_submit=["selector4"],
            confirm_cancel=["selector5"],
        )
        assert selectors.cancel_link == ["selector1"]
        assert selectors.decline_offer == ["selector2"]
        assert selectors.survey_option == ["selector3"]
        assert selectors.survey_submit == ["selector4"]
        assert selectors.confirm_cancel == ["selector5"]


class TestServiceConfig:
    """Tests for ServiceConfig dataclass."""

    def test_config_initialization(self):
        """Test ServiceConfig can be initialized with all fields."""
        selectors = ServiceSelectors(
            cancel_link=[],
            decline_offer=[],
            survey_option=[],
            survey_submit=[],
            confirm_cancel=[],
        )
        config = ServiceConfig(
            name="TestService",
            entry_url="https://example.com",
            mock_entry_url="http://localhost:8000",
            selectors=selectors,
            text_indicators={"login": ["Sign In"]},
        )
        assert config.name == "TestService"
        assert config.entry_url == "https://example.com"
        assert config.mock_entry_url == "http://localhost:8000"
        assert config.selectors is selectors
        assert config.text_indicators == {"login": ["Sign In"]}


class TestNetflixServiceInitialization:
    """Tests for NetflixService initialization."""

    def test_default_target_is_live(self):
        """Test NetflixService initializes with live target by default."""
        service = NetflixService()
        assert service.target == "live"

    def test_mock_target_initialization(self):
        """Test NetflixService can be initialized with mock target."""
        service = NetflixService(target="mock")
        assert service.target == "mock"

    def test_service_name_is_netflix(self):
        """Test service name is Netflix."""
        service = NetflixService()
        assert service.name == "Netflix"


class TestNetflixServiceEntryUrl:
    """Tests for NetflixService entry_url property."""

    def test_entry_url_returns_live_url_for_live_target(self):
        """Test entry_url returns Netflix account URL for live target."""
        service = NetflixService(target="live")
        assert service.entry_url == "https://www.netflix.com/account"

    def test_entry_url_returns_mock_url_for_mock_target(self):
        """Test entry_url returns mock server URL for mock target."""
        service = NetflixService(target="mock")
        assert service.entry_url == "http://localhost:8000/account"


class TestNetflixServiceSelectors:
    """Tests for NetflixService selectors."""

    def test_selectors_property_returns_service_selectors(self):
        """Test selectors property returns ServiceSelectors instance."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors, ServiceSelectors)

    def test_cancel_link_selectors_configured(self):
        """Test cancel link selectors are properly configured."""
        service = NetflixService()
        selectors = service.selectors
        assert len(selectors.cancel_link) > 0
        assert "[data-uia='action-cancel-membership']" in selectors.cancel_link

    def test_decline_offer_selectors_configured(self):
        """Test decline offer selectors are properly configured."""
        service = NetflixService()
        selectors = service.selectors
        assert len(selectors.decline_offer) > 0
        assert "[data-uia='continue-cancel-btn']" in selectors.decline_offer

    def test_survey_option_selectors_configured(self):
        """Test survey option selectors are properly configured."""
        service = NetflixService()
        selectors = service.selectors
        assert len(selectors.survey_option) > 0
        assert "input[type='radio']" in selectors.survey_option

    def test_survey_submit_selectors_configured(self):
        """Test survey submit selectors are properly configured."""
        service = NetflixService()
        selectors = service.selectors
        assert len(selectors.survey_submit) > 0
        assert "[data-uia='continue-btn']" in selectors.survey_submit

    def test_confirm_cancel_selectors_configured(self):
        """Test confirm cancel selectors are properly configured."""
        service = NetflixService()
        selectors = service.selectors
        assert len(selectors.confirm_cancel) > 0
        assert "[data-uia='confirm-cancel-btn']" in selectors.confirm_cancel


class TestNetflixServiceTextIndicators:
    """Tests for NetflixService text_indicators."""

    def test_text_indicators_is_dict(self):
        """Test text_indicators is a dictionary."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert isinstance(indicators, dict)

    def test_login_indicators_configured(self):
        """Test login text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "login" in indicators
        assert "Sign In" in indicators["login"]

    def test_active_indicators_configured(self):
        """Test active subscription text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "active" in indicators
        assert "Cancel Membership" in indicators["active"]

    def test_cancelled_indicators_configured(self):
        """Test cancelled subscription text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "cancelled" in indicators
        assert "Restart Membership" in indicators["cancelled"]

    def test_third_party_indicators_configured(self):
        """Test third party billing text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "third_party" in indicators
        assert "iTunes" in indicators["third_party"]

    def test_retention_indicators_configured(self):
        """Test retention offer text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "retention" in indicators
        assert "Special offer" in indicators["retention"]

    def test_survey_indicators_configured(self):
        """Test survey text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "survey" in indicators
        assert "Why are you leaving" in indicators["survey"]

    def test_confirmation_indicators_configured(self):
        """Test confirmation text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "confirmation" in indicators
        assert "Finish Cancellation" in indicators["confirmation"]

    def test_complete_indicators_configured(self):
        """Test completion text indicators are configured."""
        service = NetflixService()
        indicators = service.config.text_indicators
        assert "complete" in indicators
        assert "Cancelled" in indicators["complete"]


class TestNetflixServiceConfig:
    """Tests for NetflixService config property."""

    def test_config_property_returns_service_config(self):
        """Test config property returns ServiceConfig instance."""
        service = NetflixService()
        config = service.config
        assert isinstance(config, ServiceConfig)

    def test_config_has_correct_name(self):
        """Test config has correct service name."""
        service = NetflixService()
        assert service.config.name == "Netflix"

    def test_config_has_correct_entry_url(self):
        """Test config has correct entry URL."""
        service = NetflixService()
        assert service.config.entry_url == "https://www.netflix.com/account"

    def test_config_has_correct_mock_entry_url(self):
        """Test config has correct mock entry URL."""
        service = NetflixService()
        assert service.config.mock_entry_url == "http://localhost:8000/account"
