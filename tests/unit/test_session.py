"""Unit tests for session logging utilities.

Tests cover:
- StateTransition dataclass creation
- AICall dataclass creation
- SessionLogger directory creation
- SessionLogger log_transition functionality
- SessionLogger log_ai_call functionality
- SessionLogger complete functionality
- SessionLogger _save writes valid JSON
"""

import json
from pathlib import Path

from subterminator.utils.session import AICall, SessionLogger, StateTransition


class TestStateTransition:
    """Tests for the StateTransition dataclass."""

    def test_create_state_transition(self) -> None:
        """Should create StateTransition with all fields."""
        transition = StateTransition(
            timestamp="2026-02-03T10:30:00",
            from_state="ACCOUNT_ACTIVE",
            to_state="RETENTION_OFFER",
            trigger="click_cancel_button",
            url="https://example.com/account",
            screenshot="screenshot_001.png",
            detection_method="ai",
            confidence=0.95,
        )
        assert transition.timestamp == "2026-02-03T10:30:00"
        assert transition.from_state == "ACCOUNT_ACTIVE"
        assert transition.to_state == "RETENTION_OFFER"
        assert transition.trigger == "click_cancel_button"
        assert transition.url == "https://example.com/account"
        assert transition.screenshot == "screenshot_001.png"
        assert transition.detection_method == "ai"
        assert transition.confidence == 0.95


class TestAICall:
    """Tests for the AICall dataclass."""

    def test_create_ai_call(self) -> None:
        """Should create AICall with all fields."""
        ai_call = AICall(
            timestamp="2026-02-03T10:30:00",
            screenshot="screenshot_001.png",
            prompt_tokens=1500,
            response_tokens=250,
            state_detected="RETENTION_OFFER",
            confidence=0.92,
        )
        assert ai_call.timestamp == "2026-02-03T10:30:00"
        assert ai_call.screenshot == "screenshot_001.png"
        assert ai_call.prompt_tokens == 1500
        assert ai_call.response_tokens == 250
        assert ai_call.state_detected == "RETENTION_OFFER"
        assert ai_call.confidence == 0.92


class TestSessionLogger:
    """Tests for the SessionLogger class."""

    def test_session_directory_creation(self, tmp_path: Path) -> None:
        """Should create session directory on initialization."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        assert logger.session_dir.exists()
        assert logger.session_dir.is_dir()
        assert logger.session_dir.parent == tmp_path
        assert "netflix" in logger.session_id

    def test_session_id_format(self, tmp_path: Path) -> None:
        """Session ID should follow service_timestamp format."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="spotify",
            target="user123",
        )

        # Session ID should start with service name
        assert logger.session_id.startswith("spotify_")
        # Should have timestamp format YYYYMMDD_HHMMSS
        parts = logger.session_id.split("_")
        assert len(parts) >= 3  # spotify, date, time

    def test_initial_data_structure(self, tmp_path: Path) -> None:
        """Should initialize data with correct structure."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        assert logger.data["session_id"] == logger.session_id
        assert logger.data["service"] == "netflix"
        assert logger.data["target"] == "test@example.com"
        assert logger.data["started_at"] is not None
        assert logger.data["completed_at"] is None
        assert logger.data["result"] is None
        assert logger.data["final_state"] is None
        assert logger.data["transitions"] == []
        assert logger.data["ai_calls"] == []
        assert logger.data["error"] is None

    def test_log_transition_adds_to_list(self, tmp_path: Path) -> None:
        """log_transition should add transition to transitions list."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.log_transition(
            from_state="START",
            to_state="LOGIN_REQUIRED",
            trigger="navigate",
            url="https://netflix.com/login",
            screenshot="screenshot_001.png",
            detection_method="ai",
            confidence=0.98,
        )

        assert len(logger.data["transitions"]) == 1
        transition = logger.data["transitions"][0]
        assert transition["from_state"] == "START"
        assert transition["to_state"] == "LOGIN_REQUIRED"
        assert transition["trigger"] == "navigate"
        assert transition["url"] == "https://netflix.com/login"
        assert transition["screenshot"] == "screenshot_001.png"
        assert transition["detection_method"] == "ai"
        assert transition["confidence"] == 0.98
        assert "timestamp" in transition

    def test_log_transition_multiple(self, tmp_path: Path) -> None:
        """Should accumulate multiple transitions."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.log_transition(
            from_state="START",
            to_state="LOGIN_REQUIRED",
            trigger="navigate",
            url="https://netflix.com/login",
            screenshot="screenshot_001.png",
            detection_method="ai",
            confidence=0.95,
        )

        logger.log_transition(
            from_state="LOGIN_REQUIRED",
            to_state="ACCOUNT_ACTIVE",
            trigger="login_complete",
            url="https://netflix.com/account",
            screenshot="screenshot_002.png",
            detection_method="ai",
            confidence=0.92,
        )

        assert len(logger.data["transitions"]) == 2
        assert logger.data["transitions"][0]["to_state"] == "LOGIN_REQUIRED"
        assert logger.data["transitions"][1]["to_state"] == "ACCOUNT_ACTIVE"

    def test_log_ai_call_adds_to_list(self, tmp_path: Path) -> None:
        """log_ai_call should add AI call to ai_calls list."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.log_ai_call(
            screenshot="screenshot_001.png",
            prompt_tokens=1200,
            response_tokens=180,
            state="ACCOUNT_ACTIVE",
            confidence=0.88,
        )

        assert len(logger.data["ai_calls"]) == 1
        ai_call = logger.data["ai_calls"][0]
        assert ai_call["screenshot"] == "screenshot_001.png"
        assert ai_call["prompt_tokens"] == 1200
        assert ai_call["response_tokens"] == 180
        assert ai_call["state_detected"] == "ACCOUNT_ACTIVE"
        assert ai_call["confidence"] == 0.88
        assert "timestamp" in ai_call

    def test_log_ai_call_multiple(self, tmp_path: Path) -> None:
        """Should accumulate multiple AI calls."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.log_ai_call(
            screenshot="screenshot_001.png",
            prompt_tokens=1200,
            response_tokens=180,
            state="LOGIN_REQUIRED",
            confidence=0.90,
        )

        logger.log_ai_call(
            screenshot="screenshot_002.png",
            prompt_tokens=1300,
            response_tokens=200,
            state="ACCOUNT_ACTIVE",
            confidence=0.85,
        )

        assert len(logger.data["ai_calls"]) == 2
        assert logger.data["ai_calls"][0]["state_detected"] == "LOGIN_REQUIRED"
        assert logger.data["ai_calls"][1]["state_detected"] == "ACCOUNT_ACTIVE"

    def test_complete_sets_final_values(self, tmp_path: Path) -> None:
        """complete should set completed_at, result, final_state."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.complete(result="success", final_state="COMPLETE")

        assert logger.data["completed_at"] is not None
        assert logger.data["result"] == "success"
        assert logger.data["final_state"] == "COMPLETE"
        assert logger.data["error"] is None

    def test_complete_with_error(self, tmp_path: Path) -> None:
        """complete should record error when provided."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        logger.complete(
            result="failed",
            final_state="FAILED",
            error="Network timeout occurred",
        )

        assert logger.data["completed_at"] is not None
        assert logger.data["result"] == "failed"
        assert logger.data["final_state"] == "FAILED"
        assert logger.data["error"] == "Network timeout occurred"

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """_save should write valid JSON to session.json file."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        # Add some data
        logger.log_transition(
            from_state="START",
            to_state="LOGIN_REQUIRED",
            trigger="navigate",
            url="https://netflix.com/login",
            screenshot="screenshot_001.png",
            detection_method="ai",
            confidence=0.95,
        )

        logger.log_ai_call(
            screenshot="screenshot_001.png",
            prompt_tokens=1200,
            response_tokens=180,
            state="LOGIN_REQUIRED",
            confidence=0.95,
        )

        # Verify JSON file exists and is valid
        json_path = logger.session_dir / "session.json"
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)

        assert data["session_id"] == logger.session_id
        assert data["service"] == "netflix"
        assert data["target"] == "test@example.com"
        assert len(data["transitions"]) == 1
        assert len(data["ai_calls"]) == 1

    def test_screenshots_dir_property(self, tmp_path: Path) -> None:
        """screenshots_dir should return session directory."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        assert logger.screenshots_dir == logger.session_dir
        assert logger.screenshots_dir.exists()

    def test_session_json_updated_on_each_operation(self, tmp_path: Path) -> None:
        """JSON file should be updated after each log operation."""
        logger = SessionLogger(
            output_dir=tmp_path,
            service="netflix",
            target="test@example.com",
        )

        json_path = logger.session_dir / "session.json"

        # After init, file may not exist yet until first save
        # Log a transition triggers save
        logger.log_transition(
            from_state="START",
            to_state="LOGIN_REQUIRED",
            trigger="navigate",
            url="https://netflix.com/login",
            screenshot="screenshot_001.png",
            detection_method="ai",
            confidence=0.95,
        )

        with open(json_path) as f:
            data1 = json.load(f)
        assert len(data1["transitions"]) == 1
        assert len(data1["ai_calls"]) == 0

        # Log AI call triggers save
        logger.log_ai_call(
            screenshot="screenshot_001.png",
            prompt_tokens=1200,
            response_tokens=180,
            state="LOGIN_REQUIRED",
            confidence=0.95,
        )

        with open(json_path) as f:
            data2 = json.load(f)
        assert len(data2["transitions"]) == 1
        assert len(data2["ai_calls"]) == 1


class TestModuleExports:
    """Tests for module exports from utils package."""

    def test_exports_from_utils_init(self) -> None:
        """Classes should be importable from subterminator.utils."""
        from subterminator.utils import AICall, SessionLogger, StateTransition

        assert SessionLogger.__name__ == "SessionLogger"
        assert StateTransition.__name__ == "StateTransition"
        assert AICall.__name__ == "AICall"
