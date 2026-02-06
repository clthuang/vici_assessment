"""Session logging utilities for SubTerminator.

This module provides session tracking functionality to log the cancellation flow
with JSON output. It includes:
- StateTransition dataclass for recording state changes
- AICall dataclass for recording AI interpretation calls
- SessionLogger class for managing session data and persistence
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class StateTransition:
    """Records a state transition during the cancellation flow.

    Attributes:
        timestamp: ISO format timestamp of when the transition occurred.
        from_state: The state before the transition.
        to_state: The state after the transition.
        trigger: What triggered the transition (e.g., click, navigate).
        url: The URL at which the transition occurred.
        screenshot: Filename of the screenshot taken at transition.
        detection_method: How the state was detected (e.g., ai, selector).
        confidence: Confidence score between 0.0 and 1.0.
    """

    timestamp: str
    from_state: str
    to_state: str
    trigger: str
    url: str
    screenshot: str
    detection_method: str
    confidence: float


@dataclass
class AICall:
    """Records an AI interpretation call.

    Attributes:
        timestamp: ISO format timestamp of when the call was made.
        screenshot: Filename of the screenshot that was analyzed.
        prompt_tokens: Number of tokens in the prompt.
        response_tokens: Number of tokens in the response.
        state_detected: The state detected by the AI.
        confidence: Confidence score between 0.0 and 1.0.
    """

    timestamp: str
    screenshot: str
    prompt_tokens: int
    response_tokens: int
    state_detected: str
    confidence: float


class SessionLogger:
    """Logs session data to JSON file.

    Tracks the complete cancellation flow including state transitions,
    AI interpretation calls, and session metadata. Persists data to JSON
    after each operation for crash recovery.

    Attributes:
        session_id: Unique identifier for this session.
        session_dir: Directory where session data is stored.
        data: Dictionary containing all session data.
    """

    def __init__(self, output_dir: Path, service: str, target: str) -> None:
        """Initialize a new session logger.

        Args:
            output_dir: Parent directory where session folder will be created.
            service: Name of the service being cancelled (e.g., netflix, spotify).
            target: Target identifier (e.g., email, username).
        """
        self.session_id = f"{service}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = output_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.data: dict[str, Any] = {
            "session_id": self.session_id,
            "service": service,
            "target": target,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "final_state": None,
            "transitions": [],
            "ai_calls": [],
            "error": None,
        }

    def log_transition(
        self,
        from_state: str,
        to_state: str,
        trigger: str,
        url: str,
        screenshot: str,
        detection_method: str,
        confidence: float,
    ) -> None:
        """Log a state transition.

        Args:
            from_state: The state before the transition.
            to_state: The state after the transition.
            trigger: What triggered the transition.
            url: The URL at which the transition occurred.
            screenshot: Filename of the screenshot taken.
            detection_method: How the state was detected.
            confidence: Confidence score between 0.0 and 1.0.
        """
        transition = StateTransition(
            timestamp=datetime.now().isoformat(),
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            url=url,
            screenshot=screenshot,
            detection_method=detection_method,
            confidence=confidence,
        )
        self.data["transitions"].append(asdict(transition))
        self._save()

    def log_ai_call(
        self,
        screenshot: str,
        prompt_tokens: int,
        response_tokens: int,
        state: str,
        confidence: float,
    ) -> None:
        """Log an AI interpretation call.

        Args:
            screenshot: Filename of the screenshot that was analyzed.
            prompt_tokens: Number of tokens in the prompt.
            response_tokens: Number of tokens in the response.
            state: The state detected by the AI.
            confidence: Confidence score between 0.0 and 1.0.
        """
        ai_call = AICall(
            timestamp=datetime.now().isoformat(),
            screenshot=screenshot,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            state_detected=state,
            confidence=confidence,
        )
        self.data["ai_calls"].append(asdict(ai_call))
        self._save()

    def complete(self, result: str, final_state: str, error: str | None = None) -> None:
        """Mark session complete.

        Args:
            result: The result of the session (e.g., success, failed, aborted).
            final_state: The final state reached.
            error: Optional error message if the session failed.
        """
        self.data["completed_at"] = datetime.now().isoformat()
        self.data["result"] = result
        self.data["final_state"] = final_state
        self.data["error"] = error
        self._save()

    def _save(self) -> None:
        """Write session data to JSON file."""
        log_path = self.session_dir / "session.json"
        with open(log_path, "w") as f:
            json.dump(self.data, f, indent=2)

    @property
    def screenshots_dir(self) -> Path:
        """Directory for screenshots.

        Returns:
            Path to the session directory where screenshots should be stored.
        """
        return self.session_dir
