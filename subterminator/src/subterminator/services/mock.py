"""Mock server for serving test Netflix pages."""

import http.server
import socketserver
import threading
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


class MockRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with variant routing support."""

    def __init__(self, *args: Any, pages_dir: Path, **kwargs: Any) -> None:
        self.pages_dir = pages_dir
        super().__init__(*args, directory=str(pages_dir), **kwargs)

    def do_GET(self) -> None:
        """Handle GET with variant query parameter support."""
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        # Handle variant parameter: ?variant=retention -> cancelplan_retention.html
        variant_handled = False
        if "variant" in query:
            variant = query["variant"][0]
            # Map variant to file
            variant_map = {
                "retention": "cancelplan_retention.html",
                "survey": "cancelplan_survey.html",
                "confirm": "cancelplan_confirm.html",
                "complete": "cancelplan_complete.html",
                "cancelled": "account_cancelled.html",
                "login": "login.html",
                "error": "error.html",
            }
            if variant in variant_map:
                self.path = "/" + variant_map[variant]
                variant_handled = True

        # Default: serve account.html for /account path (only if variant not handled)
        if not variant_handled and (parsed.path == "/account" or parsed.path == "/"):
            self.path = "/account.html"

        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress logging unless verbose."""
        pass  # Silent by default


class MockServer:
    """Local HTTP server serving mock Netflix pages."""

    def __init__(self, pages_dir: Path, port: int = 8000):
        self.pages_dir = pages_dir
        self.port = port
        self._server: socketserver.TCPServer | None = None
        self._thread: threading.Thread | None = None

    def _create_handler(self) -> type[MockRequestHandler]:
        """Create a request handler class with pages_dir bound."""
        pages_dir = self.pages_dir

        class BoundHandler(MockRequestHandler):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, pages_dir=pages_dir, **kwargs)

        return BoundHandler

    def start(self) -> None:
        """Start mock server in background thread."""
        handler_class = self._create_handler()
        self._server = socketserver.TCPServer(("localhost", self.port), handler_class)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        """Stop mock server."""
        if self._server:
            self._server.shutdown()
            if self._thread:
                self._thread.join(timeout=5)
            self._server = None
            self._thread = None

    @property
    def base_url(self) -> str:
        """Get base URL for the mock server."""
        return f"http://localhost:{self.port}"
