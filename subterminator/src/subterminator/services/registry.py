"""Service registry for managing available subscription services."""

import difflib
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceInfo:
    """Information about a subscription service."""

    id: str
    name: str
    description: str
    available: bool = True


# Registry of all supported services
SERVICE_REGISTRY: list[ServiceInfo] = [
    ServiceInfo(
        id="netflix",
        name="Netflix",
        description="Video streaming service",
        available=True,
    ),
    ServiceInfo(
        id="disney",
        name="Disney+",
        description="Disney streaming service",
        available=False,
    ),
    ServiceInfo(
        id="hulu",
        name="Hulu",
        description="TV and movie streaming",
        available=False,
    ),
    ServiceInfo(
        id="spotify",
        name="Spotify",
        description="Music streaming service",
        available=False,
    ),
]


def get_all_services() -> list[ServiceInfo]:
    """Get all services, sorted: available first, then alphabetically by ID.

    Returns:
        List of all ServiceInfo objects, with available services first,
        then unavailable services, each group sorted alphabetically by ID.
    """
    available = sorted(
        [s for s in SERVICE_REGISTRY if s.available],
        key=lambda s: s.id,
    )
    unavailable = sorted(
        [s for s in SERVICE_REGISTRY if not s.available],
        key=lambda s: s.id,
    )
    return available + unavailable


def get_available_services() -> list[ServiceInfo]:
    """Get only available services.

    Returns:
        List of ServiceInfo objects where available=True.
    """
    return [s for s in SERVICE_REGISTRY if s.available]


def get_service_by_id(service_id: str) -> ServiceInfo | None:
    """Get a service by its ID (case-insensitive).

    Args:
        service_id: The service ID to look up.

    Returns:
        ServiceInfo if found, None otherwise.
    """
    service_id_lower = service_id.lower()
    for service in SERVICE_REGISTRY:
        if service.id.lower() == service_id_lower:
            return service
    return None


def suggest_service(typo: str) -> str | None:
    """Suggest a service ID for a typo using fuzzy matching.

    Only suggests from available services.

    Args:
        typo: The mistyped service ID.

    Returns:
        The closest matching service ID if found (cutoff=0.6), None otherwise.
    """
    available_ids = [s.id for s in SERVICE_REGISTRY if s.available]
    matches = difflib.get_close_matches(
        typo.lower(),
        available_ids,
        n=1,
        cutoff=0.6,
    )
    return matches[0] if matches else None
