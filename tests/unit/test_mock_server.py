"""Unit tests for MockServer.

Tests cover:
- Initialization stores pages_dir and port
- Start/stop lifecycle
- Base URL property
- Module exports
"""

import socket
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from subterminator.services.mock import MockServer


class TestMockServerInit:
    """Tests for MockServer initialization."""

    def test_init_stores_pages_dir(self, tmp_path: Path) -> None:
        """MockServer should store pages_dir."""
        server = MockServer(pages_dir=tmp_path, port=8000)
        assert server.pages_dir == tmp_path

    def test_init_stores_port(self, tmp_path: Path) -> None:
        """MockServer should store port."""
        server = MockServer(pages_dir=tmp_path, port=9999)
        assert server.port == 9999

    def test_init_default_port(self, tmp_path: Path) -> None:
        """MockServer should use default port 8000."""
        server = MockServer(pages_dir=tmp_path)
        assert server.port == 8000

    def test_init_server_is_none(self, tmp_path: Path) -> None:
        """Internal server should be None before start."""
        server = MockServer(pages_dir=tmp_path)
        assert server._server is None

    def test_init_thread_is_none(self, tmp_path: Path) -> None:
        """Internal thread should be None before start."""
        server = MockServer(pages_dir=tmp_path)
        assert server._thread is None


class TestMockServerBaseUrl:
    """Tests for base_url property."""

    def test_base_url_uses_localhost_and_port(self, tmp_path: Path) -> None:
        """base_url should return http://localhost:{port}."""
        server = MockServer(pages_dir=tmp_path, port=8888)
        assert server.base_url == "http://localhost:8888"

    def test_base_url_with_default_port(self, tmp_path: Path) -> None:
        """base_url should work with default port."""
        server = MockServer(pages_dir=tmp_path)
        assert server.base_url == "http://localhost:8000"


def get_free_port() -> int:
    """Get a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class TestMockServerLifecycle:
    """Tests for start/stop lifecycle."""

    def test_start_creates_server(self, tmp_path: Path) -> None:
        """start should create server instance."""
        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        try:
            server.start()
            assert server._server is not None
        finally:
            server.stop()

    def test_start_creates_thread(self, tmp_path: Path) -> None:
        """start should create background thread."""
        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        try:
            server.start()
            assert server._thread is not None
            assert server._thread.is_alive()
        finally:
            server.stop()

    def test_start_thread_is_daemon(self, tmp_path: Path) -> None:
        """Background thread should be daemon."""
        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        try:
            server.start()
            assert server._thread is not None
            assert server._thread.daemon is True
        finally:
            server.stop()

    def test_stop_clears_server(self, tmp_path: Path) -> None:
        """stop should clear server instance."""
        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        server.start()
        server.stop()
        assert server._server is None

    def test_stop_clears_thread(self, tmp_path: Path) -> None:
        """stop should clear thread instance."""
        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        server.start()
        server.stop()
        assert server._thread is None

    def test_stop_when_not_started(self, tmp_path: Path) -> None:
        """stop should handle case when server not started."""
        server = MockServer(pages_dir=tmp_path)
        # Should not raise
        server.stop()
        assert server._server is None
        assert server._thread is None

    def test_server_accepts_connections(self, tmp_path: Path) -> None:
        """Started server should accept HTTP connections."""
        import urllib.request

        # Create a test HTML file
        test_file = tmp_path / "account.html"
        test_file.write_text("<html><body>Test</body></html>")

        port = get_free_port()
        server = MockServer(pages_dir=tmp_path, port=port)
        try:
            server.start()
            # Give server time to start
            time.sleep(0.1)

            # Try to connect
            response = urllib.request.urlopen(f"http://localhost:{port}/account.html")
            assert response.status == 200
            content = response.read().decode()
            assert "Test" in content
        finally:
            server.stop()


class TestModuleExports:
    """Tests for module exports."""

    def test_import_from_services(self) -> None:
        """MockServer should be importable from subterminator.services."""
        from subterminator.services import MockServer

        assert MockServer is not None
        assert MockServer.__name__ == "MockServer"

    def test_import_from_mock_module(self) -> None:
        """MockServer should be importable from mock module."""
        from subterminator.services.mock import MockServer

        assert MockServer is not None
