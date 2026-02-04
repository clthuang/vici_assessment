"""Selector configuration types for browser automation.

This module provides the SelectorConfig dataclass for defining CSS selectors
with optional ARIA role-based fallbacks for more robust element targeting.
"""

from dataclasses import dataclass


@dataclass
class SelectorConfig:
    """Configuration for element selectors with CSS and optional ARIA fallback.

    Attributes:
        css: List of CSS selectors to try in order for finding elements.
        aria: Optional tuple of (role, name) for ARIA-based selection fallback.
              Example: ("button", "Submit") matches elements with role="button"
              and accessible name "Submit".
    """

    css: list[str]
    aria: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate that css list is not empty."""
        if not self.css:
            raise ValueError("css list cannot be empty")
