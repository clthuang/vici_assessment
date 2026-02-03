"""Unit tests for CLI output formatter.

Tests cover:
- PromptType enum values
- OutputFormatter step counter progression
- OutputFormatter warning output
- OutputFormatter progress display
"""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from subterminator.cli.output import OutputFormatter, PromptType
from subterminator.core.protocols import CancellationResult, State


class TestPromptType:
    """Tests for the PromptType enum."""

    def test_all_prompt_types_exist(self) -> None:
        """All required prompt types should be defined."""
        expected_types = ["AUTH", "CONFIRM", "UNKNOWN"]
        actual_types = [pt.name for pt in PromptType]
        assert actual_types == expected_types

    def test_prompt_type_values(self) -> None:
        """Prompt types should have correct string values."""
        assert PromptType.AUTH.value == "auth"
        assert PromptType.CONFIRM.value == "confirm"
        assert PromptType.UNKNOWN.value == "unknown"

    def test_prompt_types_have_unique_values(self) -> None:
        """Each prompt type should have a unique value."""
        values = [pt.value for pt in PromptType]
        assert len(values) == len(set(values))

    def test_prompt_type_is_comparable(self) -> None:
        """Prompt types should be comparable."""
        assert PromptType.AUTH == PromptType.AUTH
        assert PromptType.AUTH != PromptType.CONFIRM


class TestOutputFormatterProgress:
    """Tests for OutputFormatter.show_progress method."""

    def test_show_progress_increments_step_counter(self) -> None:
        """Step counter should increment with each call to show_progress."""
        formatter = OutputFormatter()
        assert formatter._step == 0

        with patch("sys.stdout", new_callable=StringIO):
            formatter.show_progress("START", "Beginning process")
            assert formatter._step == 1

            formatter.show_progress("ACCOUNT_ACTIVE", "Account found")
            assert formatter._step == 2

            formatter.show_progress("COMPLETE", "Done")
            assert formatter._step == 3

    def test_show_progress_outputs_state_and_message(self) -> None:
        """Progress output should contain state and message."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_progress("START", "Beginning process")
            output = mock_stdout.getvalue()

        assert "[1]" in output
        assert "START" in output
        assert "Beginning process" in output

    def test_show_progress_step_numbering_format(self) -> None:
        """Progress should show step numbers in brackets."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_progress("START", "First step")
            formatter.show_progress("ACCOUNT_ACTIVE", "Second step")
            output = mock_stdout.getvalue()

        assert "[1]" in output
        assert "[2]" in output

    def test_show_progress_with_unknown_state(self) -> None:
        """Progress should handle unknown states gracefully."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_progress("NONEXISTENT_STATE", "Testing unknown state")
            output = mock_stdout.getvalue()

        assert "NONEXISTENT_STATE" in output
        assert "Testing unknown state" in output


class TestOutputFormatterWarning:
    """Tests for OutputFormatter.show_warning method."""

    def test_show_warning_outputs_message(self) -> None:
        """Warning should output the provided message."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_warning("This is a test warning")
            output = mock_stdout.getvalue()

        assert "WARNING" in output
        assert "This is a test warning" in output

    def test_show_warning_does_not_increment_step(self) -> None:
        """Warning should not affect the step counter."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO):
            formatter.show_warning("Test warning")
            assert formatter._step == 0

            formatter.show_progress("START", "Step")
            assert formatter._step == 1

            formatter.show_warning("Another warning")
            assert formatter._step == 1


class TestOutputFormatterSuccess:
    """Tests for OutputFormatter.show_success method."""

    def test_show_success_displays_result_message(self) -> None:
        """Success output should contain result message."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=True,
            state=State.COMPLETE,
            message="Cancellation completed",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_success(result)
            output = mock_stdout.getvalue()

        assert "SUCCESSFUL" in output
        assert "Cancellation completed" in output

    def test_show_success_displays_effective_date_when_present(self) -> None:
        """Success output should include effective date if provided."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=True,
            state=State.COMPLETE,
            message="Cancellation completed",
            effective_date="2026-03-01",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_success(result)
            output = mock_stdout.getvalue()

        assert "2026-03-01" in output
        assert "Effective Date" in output

    def test_show_success_displays_session_dir_when_present(self) -> None:
        """Success output should include session directory if provided."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=True,
            state=State.COMPLETE,
            message="Cancellation completed",
            session_dir=Path("/tmp/session_123"),
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_success(result)
            output = mock_stdout.getvalue()

        assert "/tmp/session_123" in output


class TestOutputFormatterFailure:
    """Tests for OutputFormatter.show_failure method."""

    def test_show_failure_displays_result_message(self) -> None:
        """Failure output should contain result message."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=False,
            state=State.FAILED,
            message="Network timeout",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_failure(result)
            output = mock_stdout.getvalue()

        assert "FAILED" in output
        assert "Network timeout" in output

    def test_show_failure_displays_final_state(self) -> None:
        """Failure output should show the final state."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=False,
            state=State.ABORTED,
            message="User cancelled",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_failure(result)
            output = mock_stdout.getvalue()

        assert "ABORTED" in output

    def test_show_failure_includes_manual_instructions(self) -> None:
        """Failure output should include manual cancellation steps."""
        formatter = OutputFormatter()
        result = CancellationResult(
            success=False,
            state=State.FAILED,
            message="Automation failed",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_failure(result)
            output = mock_stdout.getvalue()

        assert "Manual cancellation" in output
        assert "netflix.com/account" in output


class TestOutputFormatterThirdParty:
    """Tests for OutputFormatter.show_third_party_instructions method."""

    def test_show_itunes_instructions(self) -> None:
        """Should display iTunes-specific instructions."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_third_party_instructions("itunes")
            output = mock_stdout.getvalue()

        assert "Apple" in output or "iTunes" in output
        assert "Settings" in output

    def test_show_google_instructions(self) -> None:
        """Should display Google Play-specific instructions."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_third_party_instructions("google")
            output = mock_stdout.getvalue()

        assert "Google Play" in output

    def test_show_default_instructions_for_unknown_provider(self) -> None:
        """Should display default instructions for unknown providers."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_third_party_instructions("unknown_provider")
            output = mock_stdout.getvalue()

        assert "third party" in output.lower()

    def test_provider_case_insensitive(self) -> None:
        """Provider name should be case insensitive."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_third_party_instructions("ITUNES")
            output = mock_stdout.getvalue()

        assert "Apple" in output or "iTunes" in output


class TestOutputFormatterDryRun:
    """Tests for OutputFormatter.show_dry_run_notice method."""

    def test_show_dry_run_notice(self) -> None:
        """Dry run notice should indicate no changes will be made."""
        formatter = OutputFormatter()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            formatter.show_dry_run_notice()
            output = mock_stdout.getvalue()

        assert "DRY RUN" in output
        assert "No changes" in output


class TestOutputFormatterVerboseMode:
    """Tests for OutputFormatter verbose mode."""

    def test_verbose_mode_can_be_enabled(self) -> None:
        """Formatter should accept verbose flag."""
        formatter = OutputFormatter(verbose=True)
        assert formatter.verbose is True

    def test_verbose_mode_defaults_to_false(self) -> None:
        """Verbose mode should default to False."""
        formatter = OutputFormatter()
        assert formatter.verbose is False


class TestModuleExports:
    """Tests for module exports from cli package."""

    def test_exports_from_cli_init(self) -> None:
        """OutputFormatter and PromptType should be importable from cli."""
        from subterminator.cli import OutputFormatter, PromptType

        # Verify they're the correct types
        assert OutputFormatter.__name__ == "OutputFormatter"
        assert PromptType.__name__ == "PromptType"
        assert PromptType.AUTH is not None
