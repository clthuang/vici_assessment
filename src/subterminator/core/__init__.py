"""Core module for SubTerminator business logic.

This module exports the foundational types and protocols used throughout
the SubTerminator application.
"""

from subterminator.core.ai import ClaudeInterpreter, HeuristicInterpreter
from subterminator.core.browser import PlaywrightBrowser
from subterminator.core.protocols import (
    AIInterpretation,
    AIInterpreterProtocol,
    BrowserProtocol,
    CancellationResult,
    ServiceProtocol,
    State,
)
from subterminator.core.states import CancellationStateMachine

__all__ = [
    "AIInterpretation",
    "AIInterpreterProtocol",
    "BrowserProtocol",
    "CancellationResult",
    "CancellationStateMachine",
    "ClaudeInterpreter",
    "HeuristicInterpreter",
    "PlaywrightBrowser",
    "ServiceProtocol",
    "State",
]
