"""Netflix-specific service implementation for SubTerminator."""

from dataclasses import dataclass


@dataclass
class ServiceSelectors:
    """CSS/XPath selectors for service-specific elements."""
    cancel_link: list[str]
    decline_offer: list[str]
    survey_option: list[str]
    survey_submit: list[str]
    confirm_cancel: list[str]


@dataclass
class ServiceConfig:
    """Configuration for a subscription service."""
    name: str
    entry_url: str
    mock_entry_url: str
    selectors: ServiceSelectors
    text_indicators: dict[str, list[str]]


class NetflixService:
    """Netflix-specific service implementation."""

    def __init__(self, target: str = "live"):
        """Initialize Netflix service.

        Args:
            target: "live" for real Netflix, "mock" for mock server
        """
        self.target = target
        self._config = ServiceConfig(
            name="Netflix",
            entry_url="https://www.netflix.com/account",
            mock_entry_url="http://localhost:8000/account",
            selectors=ServiceSelectors(
                cancel_link=[
                    "[data-uia='action-cancel-membership']",
                    "a:has-text('Cancel Membership')",
                    "button:has-text('Cancel Membership')",
                    ".cancel-membership-link",
                ],
                decline_offer=[
                    "[data-uia='continue-cancel-btn']",
                    "button:has-text('Continue to Cancel')",
                    "a:has-text('No Thanks')",
                    "button:has-text('No thanks')",
                ],
                survey_option=[
                    "input[type='radio']",
                    "[data-uia='cancel-reason-item']",
                    ".survey-option input",
                ],
                survey_submit=[
                    "[data-uia='continue-btn']",
                    "button:has-text('Continue')",
                    "button[type='submit']",
                ],
                confirm_cancel=[
                    "[data-uia='confirm-cancel-btn']",
                    "button:has-text('Finish Cancellation')",
                    "button:has-text('Confirm Cancellation')",
                ],
            ),
            text_indicators={
                "login": ["Sign In", "Email", "Password", "Log In"],
                "active": ["Cancel Membership", "Cancel Plan"],
                "cancelled": ["Restart Membership", "Restart your membership"],
                "third_party": [
                    "Billed through", "iTunes", "Google Play", "T-Mobile", "App Store"
                ],
                "retention": [
                    "Before you go", "Special offer", "discount",
                    "We'd hate to see you go"
                ],
                "survey": [
                    "Why are you leaving", "Reason for cancelling", "Tell us why"
                ],
                "confirmation": ["Finish Cancellation", "Confirm Cancellation"],
                "complete": [
                    "Cancelled", "Your cancellation is complete", "membership ends"
                ],
            }
        )

    @property
    def config(self) -> ServiceConfig:
        """Get service configuration."""
        return self._config

    @property
    def entry_url(self) -> str:
        """Get entry URL based on target."""
        if self.target == "mock":
            return self._config.mock_entry_url
        return self._config.entry_url

    @property
    def selectors(self) -> ServiceSelectors:
        """Get service selectors."""
        return self._config.selectors

    @property
    def name(self) -> str:
        """Get service name."""
        return self._config.name
