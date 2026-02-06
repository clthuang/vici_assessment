"""Tests for MCP orchestrator exceptions."""


from subterminator.mcp_orchestrator.exceptions import (
    CheckpointRejectedError,
    LLMError,
    MCPConnectionError,
    MCPToolError,
    OrchestratorError,
    ServiceNotFoundError,
    SnapshotValidationError,
)
from subterminator.utils.exceptions import ConfigurationError, SubTerminatorError


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_orchestrator_error_inherits_subterminator_error(self):
        """OrchestratorError inherits from SubTerminatorError."""
        err = OrchestratorError("test")
        assert isinstance(err, SubTerminatorError)
        assert isinstance(err, Exception)

    def test_mcp_connection_error_inherits(self):
        """MCPConnectionError inherits from OrchestratorError and SubTerminatorError."""
        err = MCPConnectionError("connection failed")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)
        assert str(err) == "connection failed"

    def test_mcp_tool_error_inherits(self):
        """MCPToolError inherits from OrchestratorError."""
        err = MCPToolError("tool execution failed")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)

    def test_llm_error_inherits(self):
        """LLMError inherits from OrchestratorError."""
        err = LLMError("API timeout")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)

    def test_checkpoint_rejected_error_inherits(self):
        """CheckpointRejectedError inherits from OrchestratorError."""
        err = CheckpointRejectedError("user rejected")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)

    def test_snapshot_validation_error_inherits(self):
        """SnapshotValidationError inherits from OrchestratorError."""
        err = SnapshotValidationError("parse failed")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)

    def test_service_not_found_error_inherits(self):
        """ServiceNotFoundError inherits from OrchestratorError."""
        err = ServiceNotFoundError("unknown service")
        assert isinstance(err, OrchestratorError)
        assert isinstance(err, SubTerminatorError)


class TestConfigurationErrorReexport:
    """Tests for ConfigurationError re-export."""

    def test_configuration_error_importable(self):
        """ConfigurationError can be imported from mcp_orchestrator."""
        from subterminator.mcp_orchestrator import (
            ConfigurationError as ConfigError,
        )
        # Verify it's the same class from utils
        assert ConfigError is ConfigurationError

    def test_configuration_error_not_subclass_of_orchestrator_error(self):
        """ConfigurationError is NOT a subclass of OrchestratorError."""
        err = ConfigurationError("config missing")
        # It should NOT be an OrchestratorError - it's a separate hierarchy
        assert not isinstance(err, OrchestratorError)
        # But it IS a SubTerminatorError
        assert isinstance(err, SubTerminatorError)
