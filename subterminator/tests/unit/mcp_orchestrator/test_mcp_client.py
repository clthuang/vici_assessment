"""Tests for MCP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from subterminator.mcp_orchestrator.exceptions import (
    ConfigurationError,
    MCPConnectionError,
    MCPToolError,
)
from subterminator.mcp_orchestrator.mcp_client import MCPClient


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    @patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run")
    def test_init_validates_nodejs(self, mock_run):
        """MCPClient validates Node.js version on init."""
        mock_run.return_value = MagicMock(returncode=0, stdout="v20.10.0")
        client = MCPClient()
        assert client._profile_dir is not None
        mock_run.assert_called_once()

    @patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run")
    def test_init_raises_if_nodejs_missing(self, mock_run):
        """MCPClient raises ConfigurationError if Node.js is missing."""
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(ConfigurationError) as exc_info:
            MCPClient()
        assert "Node.js is required" in str(exc_info.value)

    @patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run")
    def test_init_raises_if_nodejs_too_old(self, mock_run):
        """MCPClient raises ConfigurationError if Node.js version < 18."""
        mock_run.return_value = MagicMock(returncode=0, stdout="v16.0.0")
        with pytest.raises(ConfigurationError) as exc_info:
            MCPClient()
        assert "too old" in str(exc_info.value)

    @patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run")
    def test_init_accepts_custom_profile_dir(self, mock_run):
        """MCPClient accepts custom profile directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
        client = MCPClient(profile_dir="/custom/profile")
        assert client._profile_dir == "/custom/profile"


class TestMCPClientConnect:
    """Tests for MCPClient.connect()."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_connect_raises_if_mcp_not_installed(self, client):
        """connect() raises ConfigurationError if mcp package missing."""
        with patch.dict("sys.modules", {"mcp": None}):
            # Force import error by patching builtins.__import__
            original_import = __builtins__["__import__"]

            def mock_import(name, *args, **kwargs):
                if name == "mcp" or name.startswith("mcp."):
                    raise ImportError("No module named 'mcp'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ConfigurationError) as exc_info:
                    await client.connect()
                assert "mcp package not installed" in str(exc_info.value)


class TestMCPClientListTools:
    """Tests for MCPClient.list_tools()."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_list_tools_raises_if_not_connected(self, client):
        """list_tools() raises MCPConnectionError if not connected."""
        with pytest.raises(MCPConnectionError) as exc_info:
            await client.list_tools()
        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tools_returns_cached(self, client):
        """list_tools() returns cached tools on subsequent calls."""
        # Set up mock session and cached tools
        client._session = MagicMock()
        client._tools = [{"name": "cached_tool"}]

        result = await client.list_tools()
        assert result == [{"name": "cached_tool"}]
        # Session.list_tools should not be called
        client._session.list_tools.assert_not_called()


class TestMCPClientCallTool:
    """Tests for MCPClient.call_tool()."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_call_tool_raises_if_not_connected(self, client):
        """call_tool() raises MCPConnectionError if not connected."""
        with pytest.raises(MCPConnectionError) as exc_info:
            await client.call_tool("browser_click", {"element": "button"})
        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_extracts_text(self, client):
        """call_tool() extracts text from result content."""
        # Set up mock session
        mock_block = MagicMock()
        mock_block.text = "Tool result text"

        mock_result = MagicMock()
        mock_result.content = [mock_block]

        client._session = AsyncMock()
        client._session.call_tool = AsyncMock(return_value=mock_result)

        result = await client.call_tool("browser_snapshot", {})
        assert result == "Tool result text"
        client._session.call_tool.assert_called_once_with("browser_snapshot", {})

    @pytest.mark.asyncio
    async def test_call_tool_raises_mcp_tool_error(self, client):
        """call_tool() raises MCPToolError on failure."""
        client._session = AsyncMock()
        client._session.call_tool = AsyncMock(side_effect=Exception("Tool failed"))

        with pytest.raises(MCPToolError) as exc_info:
            await client.call_tool("browser_click", {"element": "x"})
        assert "browser_click" in str(exc_info.value)


class TestMCPClientClose:
    """Tests for MCPClient.close()."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_close_clears_state(self, client):
        """close() clears session and tools."""
        client._session = MagicMock()
        client._tools = [{"name": "tool"}]
        client._exit_stack = AsyncMock()

        await client.close()

        assert client._session is None
        assert client._tools is None
        assert client._exit_stack is None

    @pytest.mark.asyncio
    async def test_close_handles_no_connection(self, client):
        """close() handles case when not connected."""
        # Should not raise
        await client.close()
        assert client._session is None


class TestMCPClientContextManager:
    """Tests for MCPClient async context manager."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_closes(self, client):
        """Context manager calls connect on enter and close on exit."""
        client.connect = AsyncMock()
        client.close = AsyncMock()

        async with client as c:
            assert c is client
            client.connect.assert_called_once()

        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self, client):
        """Context manager calls close even on exception."""
        client.connect = AsyncMock()
        client.close = AsyncMock()

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("test error")

        client.close.assert_called_once()


class TestMCPClientReconnect:
    """Tests for MCPClient.reconnect()."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked Node.js check."""
        with patch("subterminator.mcp_orchestrator.mcp_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v20.0.0")
            yield MCPClient()

    @pytest.mark.asyncio
    async def test_reconnect_closes_and_connects(self, client):
        """reconnect() calls close then connect."""
        call_order = []
        client.close = AsyncMock(side_effect=lambda: call_order.append("close"))
        client.connect = AsyncMock(side_effect=lambda: call_order.append("connect"))
        client._tools = [{"name": "cached"}]

        await client.reconnect()

        assert call_order == ["close", "connect"]
        # Tools cache should be cleared
        assert client._tools is None
