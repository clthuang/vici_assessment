"""Unit tests for service registry module."""

import pytest

from subterminator.services.registry import (
    ServiceInfo,
    get_all_services,
    get_available_services,
    get_service_by_id,
    suggest_service,
)


def test_get_all_services_returns_all():
    """All 4 services returned including unavailable."""
    services = get_all_services()
    assert len(services) == 4
    assert all(isinstance(s, ServiceInfo) for s in services)


def test_get_all_services_ordering():
    """Available first, then unavailable, alphabetical within each."""
    services = get_all_services()
    ids = [s.id for s in services]
    assert ids == ["netflix", "disney", "hulu", "spotify"]


def test_get_available_services_filters():
    """Only available=True services returned."""
    services = get_available_services()
    assert len(services) == 1
    assert services[0].id == "netflix"
    assert all(s.available for s in services)


def test_get_service_by_id_found():
    """Returns ServiceInfo for valid ID."""
    service = get_service_by_id("netflix")
    assert service is not None
    assert service.id == "netflix"
    assert service.available is True


def test_get_service_by_id_not_found():
    """Returns None for unknown ID."""
    assert get_service_by_id("unknown") is None


def test_get_service_by_id_case_insensitive():
    """'Netflix' and 'netflix' both work."""
    assert get_service_by_id("Netflix") is not None
    assert get_service_by_id("NETFLIX") is not None
    assert get_service_by_id("netflix") is not None


def test_suggest_service_close_match():
    """'netflixx' suggests 'netflix' (uses difflib cutoff=0.6)."""
    suggestion = suggest_service("netflixx")
    assert suggestion == "netflix"


def test_suggest_service_no_match():
    """'xyz' returns None."""
    assert suggest_service("xyz") is None


def test_suggest_service_unavailable_not_suggested():
    """Unavailable services not suggested (suggest from available only)."""
    assert suggest_service("spotifi") is None
