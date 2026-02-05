"""Core module for SubTerminator business logic.

This module exports the foundational types and protocols used throughout
the SubTerminator application.
"""

from subterminator.core.browser import PlaywrightBrowser
from subterminator.core.protocols import (
    ActionPlan,
    ActionRecord,
    ActionType,
    AgentContext,
    AIInterpretation,
    AIInterpreterProtocol,
    BrowserAction,
    BrowserElement,
    BrowserProtocol,
    CancellationResult,
    ErrorRecord,
    ExecutionResult,
    PlannedAction,
    ServiceConfigProtocol,
    ServiceProtocol,
    State,
    TargetStrategy,
    ValidationResult,
)
from subterminator.core.states import CancellationStateMachine

__all__ = [
    "ActionPlan",
    "ActionRecord",
    "ActionType",
    "AgentContext",
    "AIInterpretation",
    "AIInterpreterProtocol",
    "BrowserAction",
    "BrowserElement",
    "BrowserProtocol",
    "CancellationResult",
    "CancellationStateMachine",
    "ErrorRecord",
    "ExecutionResult",
    "PlannedAction",
    "PlaywrightBrowser",
    "ServiceConfigProtocol",
    "ServiceProtocol",
    "State",
    "TargetStrategy",
    "ValidationResult",
]
