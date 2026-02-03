"""Integration tests for heuristic interpreter with mock pages.

Tests the HeuristicInterpreter against actual mock HTML pages
served by the MockServer to verify end-to-end state detection.
"""

import time

import pytest
import requests
from pathlib import Path

from subterminator.core.ai import HeuristicInterpreter
from subterminator.core.protocols import State
from subterminator.services.mock import MockServer


class TestHeuristicWithMockPages:
    """Test heuristic interpreter against actual mock pages."""

    def test_detect_account_active(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of active account page."""
        heuristic = HeuristicInterpreter()

        # Read the account.html content
        with open(mock_pages_dir / "account.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/account",
            text=text
        )

        assert result.state == State.ACCOUNT_ACTIVE
        assert result.confidence >= 0.7

    def test_detect_account_cancelled(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of cancelled account page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "account_cancelled.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/account?variant=cancelled",
            text=text
        )

        assert result.state == State.ACCOUNT_CANCELLED
        assert result.confidence >= 0.7

    def test_detect_login_required(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of login page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "login.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/login",
            text=text
        )

        assert result.state == State.LOGIN_REQUIRED
        assert result.confidence >= 0.9

    def test_detect_retention_offer(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of retention offer page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "cancelplan_retention.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/cancelplan?variant=retention",
            text=text
        )

        assert result.state == State.RETENTION_OFFER
        assert result.confidence >= 0.7

    def test_detect_exit_survey(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of exit survey page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "cancelplan_survey.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/cancelplan?variant=survey",
            text=text
        )

        assert result.state == State.EXIT_SURVEY
        assert result.confidence >= 0.7

    def test_detect_final_confirmation(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of final confirmation page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "cancelplan_confirm.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/cancelplan?variant=confirm",
            text=text
        )

        assert result.state == State.FINAL_CONFIRMATION
        assert result.confidence >= 0.7

    def test_detect_complete(self, mock_server: MockServer, mock_pages_dir: Path):
        """Test detection of completion page."""
        heuristic = HeuristicInterpreter()

        with open(mock_pages_dir / "cancelplan_complete.html") as f:
            text = f.read()

        result = heuristic.interpret(
            url=f"{mock_server.base_url}/cancelplan?variant=complete",
            text=text
        )

        assert result.state == State.COMPLETE
        assert result.confidence >= 0.7


class TestMockServerRouting:
    """Test mock server serves correct pages."""

    def test_server_starts_and_stops(self, mock_server: MockServer):
        """Test server lifecycle."""
        assert mock_server._server is not None
        assert mock_server._thread is not None
        assert mock_server._thread.is_alive()

    def test_base_url(self, mock_server: MockServer):
        """Test base URL is correct."""
        assert mock_server.base_url.startswith("http://localhost:")

    def test_serves_account_page(self, mock_server: MockServer):
        """Test server serves account page."""
        # Give server time to start
        time.sleep(0.1)
        response = requests.get(f"{mock_server.base_url}/account.html")
        assert response.status_code == 200
        assert "Cancel Membership" in response.text

    def test_serves_login_page(self, mock_server: MockServer):
        """Test server serves login page."""
        time.sleep(0.1)
        response = requests.get(f"{mock_server.base_url}/login.html")
        assert response.status_code == 200
        assert "Sign In" in response.text

    def test_serves_variant_pages(self, mock_server: MockServer):
        """Test server serves variant pages via query params."""
        time.sleep(0.1)

        # Test cancelled variant
        response = requests.get(f"{mock_server.base_url}/account?variant=cancelled")
        assert response.status_code == 200
        assert "Restart Membership" in response.text

        # Test retention variant
        response = requests.get(f"{mock_server.base_url}/cancelplan?variant=retention")
        assert response.status_code == 200
        assert "Before you go" in response.text

    def test_default_account_page(self, mock_server: MockServer):
        """Test /account path serves account.html by default."""
        time.sleep(0.1)
        response = requests.get(f"{mock_server.base_url}/account")
        assert response.status_code == 200
        assert "Cancel Membership" in response.text
