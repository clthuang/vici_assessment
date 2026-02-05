"""MCP Client for Playwright MCP server communication.

This module provides the MCPClient class for managing connections to
Playwright MCP server via stdio transport.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

from .exceptions import ConfigurationError, MCPConnectionError, MCPToolError

if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)

# Minimum required Node.js version
MIN_NODE_VERSION = 18


class MCPClient:
    """Client for communicating with Playwright MCP server.

    Uses stdio transport to communicate with the MCP server subprocess.

    Example:
        async with MCPClient() as client:
            tools = await client.list_tools()
            result = await client.call_tool("browser_navigate", {"url": "https://example.com"})
    """

    def __init__(self, profile_dir: str | None = None) -> None:
        """Initialize MCP client.

        Args:
            profile_dir: Browser profile directory. If None, uses a default.

        Raises:
            ConfigurationError: If Node.js is not installed or version < 18.
        """
        self._profile_dir = profile_dir or self._get_default_profile_dir()
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._tools: list[dict[str, Any]] | None = None

        # Validate Node.js on init
        self._validate_nodejs()

    def _get_default_profile_dir(self) -> str:
        """Get default browser profile directory.

        Uses the project's .chrome-profile directory if it exists,
        which preserves login sessions from previous browser runs.
        Falls back to a temp directory if not found.
        """
        import os

        # Use project's existing .chrome-profile directory
        # This preserves login sessions from previous runs
        project_profile = os.path.join(os.getcwd(), ".chrome-profile")
        if os.path.exists(project_profile):
            return project_profile

        # Fallback to temp directory if not found
        import tempfile

        return os.path.join(tempfile.gettempdir(), "subterminator_mcp_profile")

    def _validate_nodejs(self) -> None:
        """Validate Node.js is installed and meets minimum version.

        Raises:
            ConfigurationError: If Node.js is missing or version < 18.
        """
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise ConfigurationError(
                    "Node.js is required but not found. "
                    "Please install Node.js >= 18 from https://nodejs.org/"
                )

            # Parse version (format: v20.10.0)
            version_str = result.stdout.strip()
            if version_str.startswith("v"):
                version_str = version_str[1:]
            major_version = int(version_str.split(".")[0])

            if major_version < MIN_NODE_VERSION:
                raise ConfigurationError(
                    f"Node.js version {major_version} is too old. "
                    f"Please upgrade to Node.js >= {MIN_NODE_VERSION}."
                )
        except FileNotFoundError:
            raise ConfigurationError(
                "Node.js is required but not found. "
                "Please install Node.js >= 18 from https://nodejs.org/"
            )
        except subprocess.TimeoutExpired:
            raise ConfigurationError(
                "Node.js version check timed out. "
                "Please ensure Node.js is properly installed."
            )

    async def connect(self) -> None:
        """Connect to Playwright MCP server.

        Starts the MCP subprocess and initializes the session.

        Raises:
            MCPConnectionError: If connection fails.
            ConfigurationError: If mcp package is not installed.
        """
        # Verify mcp package is installed
        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
        except ImportError:
            raise ConfigurationError(
                "mcp package not installed. Run: pip install mcp"
            )

        try:
            # Set up server parameters
            params = StdioServerParameters(
                command="npx",
                args=["@playwright/mcp@latest", "--user-data-dir", self._profile_dir],
            )

            # Create exit stack for lifecycle management
            self._exit_stack = AsyncExitStack()

            # Start the stdio client and get streams
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )

            # Create and initialize session
            self._session = ClientSession(read_stream, write_stream)
            await self._exit_stack.enter_async_context(self._session)
            await self._session.initialize()

            logger.info("Connected to Playwright MCP server")

        except Exception as e:
            # Clean up on failure
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            self._session = None
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from MCP server.

        Returns:
            List of tool schemas.

        Raises:
            MCPConnectionError: If not connected.
        """
        if not self._session:
            raise MCPConnectionError("Not connected to MCP server")

        if self._tools is not None:
            return self._tools

        try:
            result = await self._session.list_tools()
            self._tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in result.tools
            ]
            return self._tools
        except Exception as e:
            raise MCPConnectionError(f"Failed to list tools: {e}")

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result as string.

        Raises:
            MCPConnectionError: If not connected.
            MCPToolError: If tool execution fails.
        """
        if not self._session:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            result = await self._session.call_tool(name, arguments)

            # Extract text from result content
            if result.content:
                # Content is typically a list of content blocks
                text_parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                return "\n".join(text_parts)
            return ""

        except Exception as e:
            raise MCPToolError(f"Tool '{name}' failed: {e}")

    async def reconnect(self) -> None:
        """Reconnect to MCP server after connection loss.

        Closes existing connection and establishes a new one.

        Raises:
            MCPConnectionError: If reconnection fails.
        """
        logger.info("Reconnecting to MCP server...")
        await self.close()
        self._tools = None  # Clear tool cache
        await self.connect()

    async def close(self) -> None:
        """Close connection to MCP server.

        Cleans up subprocess and resets state.
        """
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error closing MCP connection: {e}")
            self._exit_stack = None

        self._session = None
        self._tools = None

        # Allow subprocess transport cleanup callbacks to run
        # This prevents "Event loop is closed" errors during garbage collection
        await asyncio.sleep(0.1)

        logger.info("Disconnected from MCP server")

    async def __aenter__(self) -> MCPClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._session is not None
