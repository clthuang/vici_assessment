"""Core module for SubTerminator business logic.

This module exports the foundational types and protocols used throughout
the SubTerminator application.
"""

from subterminator.core.agent import AIBrowserAgent
from subterminator.core.ai import (
    ClaudeActionPlanner,
    ClaudeInterpreter,
    HeuristicInterpreter,
)
from subterminator.core.browser import PlaywrightBrowser
from subterminator.core.engine import CancellationEngine, with_retry
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
    "AIBrowserAgent",
    "AIInterpretation",
    "AIInterpreterProtocol",
    "BrowserAction",
    "BrowserElement",
    "BrowserProtocol",
    "CancellationEngine",
    "CancellationResult",
    "CancellationStateMachine",
    "ClaudeActionPlanner",
    "ClaudeInterpreter",
    "ErrorRecord",
    "ExecutionResult",
    "HeuristicInterpreter",
    "PlannedAction",
    "PlaywrightBrowser",
    "ServiceConfigProtocol",
    "ServiceProtocol",
    "State",
    "TargetStrategy",
    "ValidationResult",
    "with_retry",
]
