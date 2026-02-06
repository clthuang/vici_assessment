"""Base service configuration for MCP orchestrator.

This module defines the ServiceConfig dataclass that holds all
service-specific configuration for browser orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import CheckpointPredicate, SnapshotPredicate


@dataclass
class ServiceConfig:
    """Configuration for a specific service orchestration.

    Attributes:
        name: Service identifier (e.g., "netflix").
        initial_url: Starting URL for orchestration.
        goal_template: Template for LLM goal description. Use {service} placeholder.
        checkpoint_conditions: Predicates that trigger human approval.
            Each predicate takes (ToolCall, NormalizedSnapshot) and returns bool.
        success_indicators: Predicates that indicate successful completion.
            Each predicate takes NormalizedSnapshot and returns bool.
        failure_indicators: Predicates that indicate failure conditions.
            Each predicate takes NormalizedSnapshot and returns bool.
        system_prompt_addition: Service-specific instructions appended to system prompt.
        auth_edge_case_detectors: Predicates that detect auth-related pages.
            Each predicate takes NormalizedSnapshot and returns bool.
    """

    name: str
    initial_url: str
    goal_template: str
    checkpoint_conditions: list[CheckpointPredicate] = field(default_factory=list)
    success_indicators: list[SnapshotPredicate] = field(default_factory=list)
    failure_indicators: list[SnapshotPredicate] = field(default_factory=list)
    system_prompt_addition: str = ""
    auth_edge_case_detectors: list[SnapshotPredicate] = field(default_factory=list)
