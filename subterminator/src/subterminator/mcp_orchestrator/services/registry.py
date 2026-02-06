"""Service registry for MCP orchestrator.

This module provides the ServiceRegistry class for managing
service configurations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import ServiceNotFoundError

if TYPE_CHECKING:
    from .base import ServiceConfig


class ServiceRegistry:
    """Registry for service configurations.

    Provides a central place to register and retrieve service configs
    by name.

    Example:
        registry = ServiceRegistry()
        registry.register(netflix_config)
        config = registry.get("netflix")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._configs: dict[str, ServiceConfig] = {}

    def register(self, config: ServiceConfig) -> None:
        """Register a service configuration.

        Args:
            config: Service configuration to register.
        """
        self._configs[config.name] = config

    def get(self, name: str) -> ServiceConfig:
        """Get a service configuration by name.

        Args:
            name: Service name.

        Returns:
            Service configuration.

        Raises:
            ServiceNotFoundError: If service not registered.
        """
        if name not in self._configs:
            available = ", ".join(sorted(self._configs.keys())) or "none"
            raise ServiceNotFoundError(
                f"Service '{name}' not found. Available services: {available}"
            )
        return self._configs[name]

    def list_services(self) -> list[str]:
        """List all registered service names.

        Returns:
            List of service names.
        """
        return sorted(self._configs.keys())


# Default global registry
default_registry = ServiceRegistry()
