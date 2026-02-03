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

__all__ = [
    "MockServer",
    "NetflixService",
    "ServiceConfig",
    "ServiceInfo",
    "ServiceSelectors",
    "get_all_services",
    "get_available_services",
    "get_service_by_id",
    "suggest_service",
]
