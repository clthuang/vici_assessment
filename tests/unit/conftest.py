"""Unit test fixtures for SubTerminator.

Note: Pytest automatically discovers fixtures from parent conftest.py files,
so explicit imports are not strictly necessary. However, this file documents
which fixtures are available for unit tests and can be extended with
unit-test-specific fixtures as needed.

Available fixtures from parent conftest.py:
- mock_browser: Mock browser conforming to BrowserProtocol
- mock_ai: Mock AI interpreter with AsyncMock interpret method
- mock_heuristic: Mock heuristic interpreter with MagicMock interpret method
- mock_session: SessionLogger instance using tmp_path
- app_config: AppConfig with test-appropriate settings
- netflix_service: NetflixService configured for mock target
- state_machine: Fresh CancellationStateMachine instance
- mock_pages_dir: Path to mock_pages/netflix directory
"""

# Fixtures are inherited from parent conftest.py automatically.
# This file can be used to add unit-test-specific fixtures.

# Re-export fixtures explicitly for documentation and IDE support
from tests.conftest import (
    app_config,
    mock_ai,
    mock_browser,
    mock_heuristic,
    mock_pages_dir,
    mock_session,
    netflix_service,
    state_machine,
)

__all__ = [
    "mock_browser",
    "mock_ai",
    "mock_heuristic",
    "mock_session",
    "app_config",
    "netflix_service",
    "state_machine",
    "mock_pages_dir",
]
