"""Core module for SubTerminator business logic.

This module exports the foundational types and protocols used throughout
the SubTerminator application.
"""

from subterminator.core.protocols import (
    AIInterpretation,
    AIInterpreterProtocol,
    BrowserProtocol,
    CancellationResult,
    ServiceProtocol,
    State,
)

__all__ = [
    "AIInterpretation",
    "AIInterpreterProtocol",
    "BrowserProtocol",
    "CancellationResult",
    "ServiceProtocol",
    "State",
]
