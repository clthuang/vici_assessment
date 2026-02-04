"""Unit tests for service factory functions."""

import pytest

from subterminator.services import create_service, get_mock_pages_dir
from subterminator.services.netflix import NetflixService


class TestCreateService:
    """Tests for create_service factory function."""

    def test_create_netflix_service_live(self):
        """Test create_service returns NetflixService with live target."""
        service = create_service("netflix", "live")
        assert isinstance(service, NetflixService)
        assert service.target == "live"

    def test_create_netflix_service_mock(self):
        """Test create_service returns NetflixService with mock target."""
        service = create_service("netflix", "mock")
        assert isinstance(service, NetflixService)
        assert service.target == "mock"

    def test_create_netflix_service_default_target_is_live(self):
        """Test create_service('netflix') defaults to live target."""
        service = create_service("netflix")
        assert isinstance(service, NetflixService)
        assert service.target == "live"

    def test_create_service_case_insensitive(self):
        """Test create_service is case insensitive."""
        service_upper = create_service("NETFLIX")
        service_mixed = create_service("Netflix")
        service_lower = create_service("netflix")

        assert isinstance(service_upper, NetflixService)
        assert isinstance(service_mixed, NetflixService)
        assert isinstance(service_lower, NetflixService)

    def test_create_service_unknown_raises_value_error(self):
        """Test create_service('unknown') raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            create_service("unknown")
        assert "Unknown service 'unknown'" in str(excinfo.value)

    def test_create_service_typo_suggests_correction(self):
        """Test create_service with typo includes suggestion in error message."""
        with pytest.raises(ValueError) as excinfo:
            create_service("netflx")  # typo missing 'i'
        error_msg = str(excinfo.value)
        assert "Did you mean 'netflix'?" in error_msg


class TestGetMockPagesDir:
    """Tests for get_mock_pages_dir function."""

    def test_get_mock_pages_dir_netflix(self):
        """Test get_mock_pages_dir returns correct path for netflix."""
        path = get_mock_pages_dir("netflix")
        assert path == "mock_pages/netflix"

    def test_get_mock_pages_dir_case_insensitive(self):
        """Test get_mock_pages_dir normalizes to lowercase."""
        path = get_mock_pages_dir("NETFLIX")
        assert path == "mock_pages/netflix"
