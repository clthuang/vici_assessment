"""Netflix-specific service implementation for SubTerminator."""

from dataclasses import dataclass

from subterminator.services.selectors import SelectorConfig


@dataclass
class ServiceSelectors:
    """CSS/XPath selectors for service-specific elements with ARIA fallbacks."""

    cancel_link: SelectorConfig
    decline_offer: SelectorConfig
    survey_option: SelectorConfig
    survey_submit: SelectorConfig
    confirm_cancel: SelectorConfig


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
            entry_url="https://www.netflix.com/account/membership",
            mock_entry_url="http://localhost:8000/account",
            selectors=ServiceSelectors(
                cancel_link=SelectorConfig(
                    css=[
                        # New: Click "Manage membership" to navigate to cancel page
                        "[data-uia='account-overview-page+membership-card+manage-membership']",
                        "a:has-text('Manage membership')",
                        # Original: Cancel button on membership page
                        "[data-uia='action-cancel-membership']",
                        "a:has-text('Cancel Membership')",
                        "button:has-text('Cancel Membership')",
                        ".cancel-membership-link",
                    ],
                    aria=("link", "Manage membership"),
                ),
                decline_offer=SelectorConfig(
                    css=[
                        "[data-uia='continue-cancel-btn']",
                        "button:has-text('Continue to Cancel')",
                        "a:has-text('No Thanks')",
                        "button:has-text('No thanks')",
                    ],
                    aria=("button", "Continue to Cancel"),
                ),
                survey_option=SelectorConfig(
                    css=[
                        "input[type='radio']",
                        "[data-uia='cancel-reason-item']",
                        ".survey-option input",
                    ],
                    aria=None,  # Radio buttons vary, skip ARIA
                ),
                survey_submit=SelectorConfig(
                    css=[
                        "[data-uia='continue-btn']",
                        "button:has-text('Continue')",
                        "button[type='submit']",
                    ],
                    aria=("button", "Continue"),
                ),
                confirm_cancel=SelectorConfig(
                    css=[
                        "[data-uia='action-finish-cancellation']",
                        "[data-uia='confirm-cancel-btn']",
                        "button:has-text('Finish Cancellation')",
                        "button:has-text('Confirm Cancellation')",
                    ],
                    aria=("button", "Finish Cancellation"),
                ),
            ),
            text_indicators={
                "login": ["Sign In", "Email", "Password", "Log In"],
                "active": ["Cancel Membership", "Cancel Plan", "Manage membership"],
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

    @property
    def service_id(self) -> str:
        """Get unique service identifier."""
        return "netflix"
