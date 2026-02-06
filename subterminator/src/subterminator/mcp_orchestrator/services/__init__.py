"""Service configuration for MCP orchestrator.

This subpackage defines service-specific configurations for browser
orchestration, including checkpoint conditions, success/failure indicators,
and service-specific prompts.
"""

from .base import ServiceConfig
from .registry import ServiceRegistry, default_registry
from . import netflix  # noqa: F401 — triggers auto-registration of NETFLIX_CONFIG

__all__ = [
    "ServiceConfig",
    "ServiceRegistry",
    "default_registry",
]
