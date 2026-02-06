"""Services module for external integrations."""

from subterminator.services.mock import MockServer
from subterminator.services.netflix import (
    NetflixService,
    ServiceConfig,
    ServiceSelectors,
)
from subterminator.services.registry import (
    ServiceInfo,
    get_all_services,
    get_available_services,
    get_service_by_id,
    suggest_service,
)


def get_mock_pages_dir(service_id: str) -> str:
    """Get mock pages directory for a service.

    Args:
        service_id: Service identifier (e.g., "netflix")

    Returns:
        Path to mock pages directory for the service
    """
    return f"mock_pages/{service_id.lower()}"


__all__ = [
    "MockServer",
    "NetflixService",
    "ServiceConfig",
    "ServiceInfo",
    "ServiceSelectors",
    "get_all_services",
    "get_available_services",
    "get_mock_pages_dir",
    "get_service_by_id",
    "suggest_service",
]
