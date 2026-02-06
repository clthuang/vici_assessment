"""Interactive prompts for service selection.

This module provides functions for interactive terminal prompts,
including TTY detection and service selection via questionary.
"""

import os
import sys

import questionary

from subterminator.cli.accessibility import get_questionary_style
from subterminator.services.registry import get_all_services


def is_interactive(no_input_flag: bool = False) -> bool:
    """Determine if the terminal is interactive.

    Checks various conditions to determine if interactive prompts should be shown.

    Args:
        no_input_flag: If True, forces non-interactive mode (highest precedence).

    Returns:
        True if the terminal is interactive and prompts should be shown,
        False otherwise.
    """
    # no_input_flag has highest precedence
    if no_input_flag:
        return False

    # Check for environment variables that disable prompts
    if "SUBTERMINATOR_NO_PROMPTS" in os.environ:
        return False

    if "CI" in os.environ:
        return False

    # Check if stdin and stdout are TTYs
    return sys.stdin.isatty() and sys.stdout.isatty()


def show_services_help() -> None:
    """Print a formatted list of all supported services.

    Displays each service with its name, description, and availability status
    ([Available] or [Coming Soon]).
    """
    print("--- Supported Services ---")
    for service in get_all_services():
        status = "[Available]" if service.available else "[Coming Soon]"
        print(f"  {service.name}: {service.description} {status}")


def select_service(plain: bool = False) -> str | None:
    """Prompt the user to select a service interactively.

    Displays a menu of available services using questionary.
    If the user selects the Help option, the service list is shown
    and the menu is re-displayed.

    Args:
        plain: If True, use plain styling (no colors).

    Returns:
        The selected service ID, or None if the user cancels (Ctrl+C).
    """
    services = get_all_services()
    style = None if plain else get_questionary_style()

    while True:
        # Build choices list
        choices: list[questionary.Choice | questionary.Separator] = []
        for service in services:
            status = "[Available]" if service.available else "[Coming Soon]"
            title = f"{service.name} - {service.description} {status}"
            # disabled expects str (reason) or None
            disabled_reason = "Coming soon" if not service.available else None
            choices.append(
                questionary.Choice(
                    title=title, value=service.id, disabled=disabled_reason
                )
            )

        # Add separator and help option
        choices.append(questionary.Separator())
        choices.append(
            questionary.Choice(title="Help - Show service details", value="__help__")
        )

        result: str | None = questionary.select(
            "Select a service to cancel:",
            choices=choices,
            style=style,
        ).ask()

        if result == "__help__":
            show_services_help()
            continue

        return result
