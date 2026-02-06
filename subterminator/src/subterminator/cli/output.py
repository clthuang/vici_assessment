"""CLI output formatting utilities for SubTerminator.

This module provides the OutputFormatter class for formatting and displaying
CLI output including progress indicators, warnings, and human prompts.
"""

from enum import Enum


class PromptType(Enum):
    """Types of human prompts."""

    AUTH = "auth"
    CONFIRM = "confirm"
    UNKNOWN = "unknown"


class OutputFormatter:
    """Formats and displays CLI output.

    Provides methods for displaying progress indicators, warnings,
    and human prompts with consistent formatting.

    Attributes:
        verbose: Whether to enable verbose output mode.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the output formatter.

        Args:
            verbose: Enable verbose output mode. Defaults to False.
        """
        self.verbose = verbose
        self._step = 0

    def show_progress(self, state: str, message: str) -> None:
        """Show step indicator with state and message.

        Increments the internal step counter and displays a formatted
        progress message with color-coded state.

        Args:
            state: The current state name (e.g., "START", "COMPLETE").
            message: A descriptive message for the current step.
        """
        self._step += 1
        prefix = f"[{self._step}]"

        # Color coding (ANSI escape codes)
        state_colors = {
            "START": "\033[36m",  # Cyan
            "LOGIN_REQUIRED": "\033[33m",  # Yellow
            "ACCOUNT_ACTIVE": "\033[32m",  # Green
            "ACCOUNT_CANCELLED": "\033[32m",  # Green
            "THIRD_PARTY_BILLING": "\033[31m",  # Red
            "RETENTION_OFFER": "\033[33m",  # Yellow
            "EXIT_SURVEY": "\033[36m",  # Cyan
            "FINAL_CONFIRMATION": "\033[33m",  # Yellow
            "COMPLETE": "\033[32m",  # Green
            "ABORTED": "\033[31m",  # Red
            "FAILED": "\033[31m",  # Red
            "UNKNOWN": "\033[35m",  # Magenta
        }
        reset = "\033[0m"
        color = state_colors.get(state, "")

        print(f"{prefix} {color}{state}{reset}: {message}")

    def show_human_prompt(self, prompt_type: PromptType, timeout: int = 0) -> str:
        """Show human prompt and get input.

        Displays a prompt message based on the prompt type and waits for
        user input.

        Args:
            prompt_type: The type of prompt to display.
            timeout: Optional timeout in seconds (0 means no timeout).

        Returns:
            The user's response, stripped and lowercased.
        """
        prompts = {
            PromptType.AUTH: (
                "\n" + "=" * 60 + "\n"
                "AUTHENTICATION REQUIRED\n"
                "Please log in to Netflix in the browser window.\n"
                "Press Enter when you have logged in...\n" + "=" * 60 + "\n"
            ),
            PromptType.CONFIRM: (
                "\n" + "=" * 60 + "\n"
                "\033[33mWARNING: FINAL CONFIRMATION\033[0m\n"
                "This action will cancel your Netflix subscription.\n"
                "You will lose access at the end of your billing period.\n"
                "\n"
                "\033[31mIMPORTANT: ALL PROFILES on this account "
                "will lose access.\033[0m\n"
                "If you share this account, please inform other users.\n"
                "\n"
                "Type 'confirm' to proceed, or anything else to abort: "
            ),
            PromptType.UNKNOWN: (
                "\n" + "=" * 60 + "\n"
                "UNKNOWN PAGE STATE\n"
                "Could not automatically detect the current page.\n"
                "Please navigate manually if needed, then press Enter...\n"
                + "=" * 60
                + "\n"
            ),
        }

        message = prompts.get(prompt_type, "Press Enter to continue...")
        print(message, end="")

        try:
            response = input()
            return response.strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    def show_warning(self, message: str) -> None:
        """Show warning message.

        Displays a formatted warning message in yellow.

        Args:
            message: The warning message to display.
        """
        print(f"\n\033[33m⚠ WARNING: {message}\033[0m\n")

    def show_third_party_instructions(self, provider: str) -> None:
        """Show provider-specific cancellation instructions.

        Displays instructions for cancelling through third-party billing
        providers such as iTunes or Google Play.

        Args:
            provider: The billing provider name (e.g., "itunes", "google").
        """
        instructions = {
            "itunes": (
                "Your Netflix subscription is billed through Apple/iTunes.\n"
                "To cancel:\n"
                "  1. Open Settings on your iPhone/iPad\n"
                "  2. Tap your name at the top\n"
                "  3. Tap 'Subscriptions'\n"
                "  4. Select Netflix and tap 'Cancel Subscription'"
            ),
            "google": (
                "Your Netflix subscription is billed through Google Play.\n"
                "To cancel:\n"
                "  1. Open Google Play Store app\n"
                "  2. Tap Menu > Subscriptions\n"
                "  3. Select Netflix and tap 'Cancel subscription'"
            ),
            "default": (
                "Your Netflix subscription is billed through a third party.\n"
                "Please cancel through that provider's subscription management."
            ),
        }

        print("\n" + "=" * 60)
        print("\033[33mTHIRD-PARTY BILLING DETECTED\033[0m")
        print("=" * 60)
        print(instructions.get(provider.lower(), instructions["default"]))
        print("=" * 60 + "\n")

    def show_dry_run_notice(self) -> None:
        """Show dry-run mode notice.

        Displays a notice indicating that the CLI is running in dry-run
        mode and no changes will be made.
        """
        print("\n\033[36m[DRY RUN MODE]\033[0m No changes will be made.\n")
