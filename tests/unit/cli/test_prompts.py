"""Tests for prompts module."""

import sys
from unittest.mock import MagicMock, patch


def test_is_interactive_tty(monkeypatch):
    """True when both stdin/stdout are TTY"""
    # Clear any cached import
    if "subterminator.cli.prompts" in sys.modules:
        del sys.modules["subterminator.cli.prompts"]

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)
    monkeypatch.delenv("SUBTERMINATOR_NO_PROMPTS", raising=False)
    monkeypatch.delenv("CI", raising=False)

    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is True


def test_is_interactive_no_input_flag(monkeypatch):
    """False when no_input_flag=True (highest precedence)"""
    # Clear any cached import
    if "subterminator.cli.prompts" in sys.modules:
        del sys.modules["subterminator.cli.prompts"]

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)
    monkeypatch.delenv("SUBTERMINATOR_NO_PROMPTS", raising=False)
    monkeypatch.delenv("CI", raising=False)

    from subterminator.cli.prompts import is_interactive
    assert is_interactive(no_input_flag=True) is False


def test_is_interactive_no_prompts_env(monkeypatch):
    """False when SUBTERMINATOR_NO_PROMPTS set"""
    # Clear any cached import
    if "subterminator.cli.prompts" in sys.modules:
        del sys.modules["subterminator.cli.prompts"]

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)
    monkeypatch.setenv("SUBTERMINATOR_NO_PROMPTS", "1")
    monkeypatch.delenv("CI", raising=False)

    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False


def test_is_interactive_ci_env(monkeypatch):
    """False when CI env var set"""
    # Clear any cached import
    if "subterminator.cli.prompts" in sys.modules:
        del sys.modules["subterminator.cli.prompts"]

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)
    monkeypatch.delenv("SUBTERMINATOR_NO_PROMPTS", raising=False)
    monkeypatch.setenv("CI", "1")

    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False


def test_is_interactive_not_tty(monkeypatch):
    """False when stdin or stdout not TTY"""
    # Clear any cached import
    if "subterminator.cli.prompts" in sys.modules:
        del sys.modules["subterminator.cli.prompts"]

    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)
    monkeypatch.delenv("SUBTERMINATOR_NO_PROMPTS", raising=False)
    monkeypatch.delenv("CI", raising=False)

    from subterminator.cli.prompts import is_interactive
    assert is_interactive() is False


def test_show_services_help_output(capsys):
    """Prints formatted service list with [Available]/[Coming Soon]"""
    from subterminator.cli.prompts import show_services_help
    show_services_help()
    captured = capsys.readouterr()
    assert "Netflix" in captured.out
    assert "[Available]" in captured.out
    assert "[Coming Soon]" in captured.out


def test_select_service_returns_selection():
    """Returns service ID when user selects (mock questionary)"""
    with patch("subterminator.cli.prompts.questionary") as mock_questionary:
        mock_questionary.select.return_value.ask.return_value = "netflix"
        from subterminator.cli.prompts import select_service
        assert select_service() == "netflix"


def test_select_service_returns_none_on_cancel():
    """Returns None when questionary.ask() returns None (Ctrl+C)"""
    with patch("subterminator.cli.prompts.questionary") as mock_questionary:
        mock_questionary.select.return_value.ask.return_value = None
        from subterminator.cli.prompts import select_service
        assert select_service() is None


def test_select_service_help_loop(capsys):
    """Re-displays menu after __help__ selection"""
    with patch("subterminator.cli.prompts.questionary") as mock_questionary:
        mock_questionary.select.return_value.ask.side_effect = ["__help__", "netflix"]
        # Need to provide Choice and Separator for when select_service builds choices
        mock_questionary.Choice = MagicMock(
            side_effect=lambda title, value, disabled=None: MagicMock(
                title=title, value=value
            )
        )
        mock_questionary.Separator = MagicMock(return_value=MagicMock())
        from subterminator.cli.prompts import select_service
        result = select_service()
        assert result == "netflix"
        captured = capsys.readouterr()
        assert "Netflix" in captured.out
