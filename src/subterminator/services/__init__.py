"""Services module for external integrations."""

from subterminator.core.protocols import ServiceProtocol
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


def create_service(service_id: str, target: str = "live") -> ServiceProtocol:
    """Create a service instance by ID.

    Args:
        service_id: Service identifier (e.g., "netflix")
        target: "live" or "mock"

    Returns:
        Service instance implementing ServiceProtocol

    Raises:
        ValueError: If service_id is unknown
    """
    service_id_lower = service_id.lower()
    if service_id_lower == "netflix":
        return NetflixService(target=target)

    # Get suggestion for typo
    suggestion = suggest_service(service_id)
    if suggestion:
        msg = f"Unknown service '{service_id}'. Did you mean '{suggestion}'?"
        raise ValueError(msg)
    raise ValueError(f"Unknown service '{service_id}'")


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
    "create_service",
    "get_all_services",
    "get_available_services",
    "get_mock_pages_dir",
    "get_service_by_id",
    "suggest_service",
]
