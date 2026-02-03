"""Accessibility utilities for terminal output.

This module provides functions to detect and respect user accessibility preferences,
including support for the NO_COLOR standard (https://no-color.org/).
"""

import os

from questionary import Style


def should_use_colors() -> bool:
    """Determine if colors should be used in terminal output.

    Returns False if:
    - NO_COLOR environment variable is set (any value, including empty string)
    - TERM environment variable is set to "dumb"

    Returns True otherwise.
    """
    # Respect NO_COLOR standard: if set (any value including empty), no colors
    if "NO_COLOR" in os.environ:
        return False

    # Respect TERM=dumb for compatibility with minimal terminals
    if os.environ.get("TERM") == "dumb":
        return False

    return True


def should_use_animations() -> bool:
    """Determine if animations should be used in terminal output.

    Returns False if:
    - should_use_colors() returns False (inherits color preferences)
    - SUBTERMINATOR_PLAIN environment variable is set

    Returns True otherwise.
    """
    # If colors are disabled, animations should also be disabled
    if not should_use_colors():
        return False

    # Check for explicit plain mode setting
    if "SUBTERMINATOR_PLAIN" in os.environ:
        return False

    return True


def get_questionary_style() -> Style | None:
    """Get the questionary Style object for prompts.

    Returns None if colors are disabled, otherwise returns a Style object
    with the SubTerminator theme.
    """
    if not should_use_colors():
        return None

    return Style(
        [
            ("answer", "fg:cyan"),
            ("question", "fg:cyan bold"),
            ("pointer", "fg:green bold"),
        ]
    )
