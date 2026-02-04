"""Unit tests for Netflix service implementation."""


from subterminator.services.netflix import (
    NetflixService,
    ServiceConfig,
    ServiceSelectors,
)
from subterminator.services.selectors import SelectorConfig


class TestServiceSelectors:
    """Tests for ServiceSelectors dataclass."""

    def test_selectors_initialization_with_selector_config(self):
        """Test ServiceSelectors can be initialized with SelectorConfig fields."""
        selectors = ServiceSelectors(
            cancel_link=SelectorConfig(
                css=["selector1"], aria=("link", "Cancel")
            ),
            decline_offer=SelectorConfig(
                css=["selector2"], aria=("button", "Continue")
            ),
            survey_option=SelectorConfig(css=["selector3"], aria=None),
            survey_submit=SelectorConfig(
                css=["selector4"], aria=("button", "Submit")
            ),
            confirm_cancel=SelectorConfig(
                css=["selector5"], aria=("button", "Confirm")
            ),
        )
        assert isinstance(selectors.cancel_link, SelectorConfig)
        assert isinstance(selectors.decline_offer, SelectorConfig)
        assert isinstance(selectors.survey_option, SelectorConfig)
        assert isinstance(selectors.survey_submit, SelectorConfig)
        assert isinstance(selectors.confirm_cancel, SelectorConfig)

    def test_each_selector_has_css_and_aria_attributes(self):
        """Test each selector has .css and .aria attributes."""
        selectors = ServiceSelectors(
            cancel_link=SelectorConfig(css=["css1"], aria=("link", "Cancel")),
            decline_offer=SelectorConfig(css=["css2"], aria=("button", "Decline")),
            survey_option=SelectorConfig(css=["css3"], aria=None),
            survey_submit=SelectorConfig(css=["css4"], aria=("button", "Submit")),
            confirm_cancel=SelectorConfig(css=["css5"], aria=("button", "Confirm")),
        )
        # Each selector should have .css and .aria attributes
        assert hasattr(selectors.cancel_link, "css")
        assert hasattr(selectors.cancel_link, "aria")
        assert selectors.cancel_link.css == ["css1"]
        assert selectors.cancel_link.aria == ("link", "Cancel")
        # Check aria can be None
        assert selectors.survey_option.aria is None


class TestServiceConfig:
    """Tests for ServiceConfig dataclass."""

    def test_config_initialization(self):
        """Test ServiceConfig can be initialized with all fields."""
        selectors = ServiceSelectors(
            cancel_link=SelectorConfig(css=["sel1"]),
            decline_offer=SelectorConfig(css=["sel2"]),
            survey_option=SelectorConfig(css=["sel3"]),
            survey_submit=SelectorConfig(css=["sel4"]),
            confirm_cancel=SelectorConfig(css=["sel5"]),
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
        """Test selectors property returns ServiceSelectors instance (not dict)."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors, ServiceSelectors)
        # Verify it's NOT a dict
        assert not isinstance(selectors, dict)

    def test_service_id_property_returns_netflix(self):
        """Test service_id property returns 'netflix'."""
        service = NetflixService()
        assert service.service_id == "netflix"

    def test_cancel_link_selectors_configured(self):
        """Test cancel link selectors are properly configured as SelectorConfig."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors.cancel_link, SelectorConfig)
        assert len(selectors.cancel_link.css) > 0
        assert "[data-uia='action-cancel-membership']" in selectors.cancel_link.css

    def test_cancel_link_has_aria_fallback(self):
        """Test cancel link has ARIA fallback."""
        service = NetflixService()
        selectors = service.selectors
        assert selectors.cancel_link.aria == ("link", "Cancel Membership")

    def test_decline_offer_selectors_configured(self):
        """Test decline offer selectors are properly configured as SelectorConfig."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors.decline_offer, SelectorConfig)
        assert len(selectors.decline_offer.css) > 0
        assert "[data-uia='continue-cancel-btn']" in selectors.decline_offer.css

    def test_decline_offer_has_aria_fallback(self):
        """Test decline offer has ARIA fallback."""
        service = NetflixService()
        selectors = service.selectors
        assert selectors.decline_offer.aria == ("button", "Continue to Cancel")

    def test_survey_option_selectors_configured(self):
        """Test survey option selectors are properly configured as SelectorConfig."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors.survey_option, SelectorConfig)
        assert len(selectors.survey_option.css) > 0
        assert "input[type='radio']" in selectors.survey_option.css

    def test_survey_option_has_no_aria_fallback(self):
        """Test survey option has no ARIA fallback (radio buttons vary)."""
        service = NetflixService()
        selectors = service.selectors
        assert selectors.survey_option.aria is None

    def test_survey_submit_selectors_configured(self):
        """Test survey submit selectors are properly configured as SelectorConfig."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors.survey_submit, SelectorConfig)
        assert len(selectors.survey_submit.css) > 0
        assert "[data-uia='continue-btn']" in selectors.survey_submit.css

    def test_survey_submit_has_aria_fallback(self):
        """Test survey submit has ARIA fallback."""
        service = NetflixService()
        selectors = service.selectors
        assert selectors.survey_submit.aria == ("button", "Continue")

    def test_confirm_cancel_selectors_configured(self):
        """Test confirm cancel selectors are properly configured as SelectorConfig."""
        service = NetflixService()
        selectors = service.selectors
        assert isinstance(selectors.confirm_cancel, SelectorConfig)
        assert len(selectors.confirm_cancel.css) > 0
        assert "[data-uia='confirm-cancel-btn']" in selectors.confirm_cancel.css

    def test_confirm_cancel_has_aria_fallback(self):
        """Test confirm cancel has ARIA fallback."""
        service = NetflixService()
        selectors = service.selectors
        assert selectors.confirm_cancel.aria == ("button", "Finish Cancellation")


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
