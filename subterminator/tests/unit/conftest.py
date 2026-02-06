"""Unit test fixtures for SubTerminator.

Note: Pytest automatically discovers fixtures from parent conftest.py files,
so explicit imports are not strictly necessary. However, this file documents
which fixtures are available for unit tests and can be extended with
unit-test-specific fixtures as needed.

Available fixtures from parent conftest.py:
- mock_session: SessionLogger instance using tmp_path
- app_config: AppConfig with test-appropriate settings
- netflix_service: NetflixService configured for mock target
- mock_pages_dir: Path to mock_pages/netflix directory
"""

# Fixtures are inherited from parent conftest.py automatically.
# This file can be used to add unit-test-specific fixtures.

# Re-export fixtures explicitly for documentation and IDE support
from tests.conftest import (
    app_config,
    mock_pages_dir,
    mock_session,
    netflix_service,
)

__all__ = [
    "app_config",
    "mock_pages_dir",
    "mock_session",
    "netflix_service",
]
