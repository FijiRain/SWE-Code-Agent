"""Asynchronous MCP client that talks to a server over stdio or HTTP."""
from ..models.ToolSpec import ToolSpec

from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.client.stdio import stdio_client
from typing import Dict, List
from contextlib import AsyncExitStack
from urllib.parse import urlparse
import shlex
import asyncio
import os
import sys
import shutil


class McpToolError(Exception):
    """Raised when an MCP tool reports an error."""


class McpConnectionError(Exception):
    """Raised when the MCP server cannot be reached or initialized."""


def check_server_command(parts: List[str]) -> None:
    """Fail early, with a clear message, if the server cannot be started.

    Check that the program exists in the PATH and, for a Python command,
    that the script given as first non-option argument exists.

    Args:
        parts: The server command split into program and arguments.

    Raises:
        McpConnectionError: If the program or the Python script is missing.
    """
    program = parts[0]
    if shutil.which(program) is None:
        raise McpConnectionError(
            f"MCP server program not found or not executable: '{program}'"
        )
    is_python = (os.path.basename(program).startswith("python")
                 or program == sys.executable)
    if not is_python:
        return
    for arg in parts[1:]:
        if arg in ("-c", "-m"):
            return
        if arg.startswith("-"):
            continue
        if not os.path.isfile(arg):
            raise McpConnectionError(
                f"MCP server script not found: '{arg}' "
                f"(looked in {os.getcwd()})"
            )
        return


class McpClient:
    """Client of an MCP server, launched over stdio or reached by HTTP."""

    def __init__(self, command: str):
        """Parse and check the command that starts the MCP server.

        Args:
            command: Shell-like command line that starts the server.

        Raises:
            McpConnectionError: If the command is invalid or not runnable.
            ValueError: If the command is empty.
        """
        self._url: str | None = None
        kind = self.server_kind(command)
        if kind == "http":
            self._url = command
        else:
            try:
                parts = shlex.split(command)
            except ValueError as e:
                raise McpConnectionError(
                    f"Invalid MCP server command: {e}") from e
            if not parts:
                raise ValueError("Empty MCP Server command")
            check_server_command(parts)
            self._params = StdioServerParameters(
                command=parts[0],
                args=parts[1:]
            )
        self._stack = AsyncExitStack()

    @staticmethod
    def server_kind(command: str) -> str:
        """Return "http" if the command is an URL, "stdio" otherwise.

        Raises:
            McpConnectionError: If the URL is not http(s) or has no host.
        """
        if "://" not in command:
            return "stdio"
        parsed = urlparse(command)
        if parsed.scheme not in ("http", "https"):
            raise McpConnectionError(
                f"Unsupported URL scheme '{parsed.scheme}' in '{command}': "
                "only http and https are supported"
            )
        if not parsed.hostname:
            raise McpConnectionError(
                f"Invalid MCP server URL (no host): '{command}'"
            )
        return "http"

    async def check_http_reachable(self) -> None:
        """Check that something listens on the host and port of the URL.

        Raises:
            McpConnectionError: If no connection can be opened within
                3 seconds.
        """
        parse = urlparse(self._url or "")
        port = parse.port or (443 if parse.scheme == "https" else 80)
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(parse.hostname, port),
                timeout=3
            )
        except (OSError, asyncio.TimeoutError) as e:
            raise McpConnectionError(
                f"Nothing answers at {parse.hostname}:{port}: "
                "is the MCP server running?"
            ) from e
        writer.close()
        await writer.wait_closed()

    async def connect(self) -> None:
        """Start the server and initialize the MCP session.

        Raises:
            McpConnectionError: If the server cannot be started or does not
                finish initialization within 10 seconds.
        """
        if self._url:
            await self.check_http_reachable()

        try:
            if self._url:
                transport = streamable_http_client(self._url)
            else:
                transport = stdio_client(self._params)
            streams = await self._stack.enter_async_context(
                transport
            )
            read, write = streams[0], streams[1]
            self._session = await self._stack.enter_async_context(
                ClientSession(read, write)
                )
            await asyncio.wait_for(
                self._session.initialize(),
                timeout=10
            )
        except Exception as e:
            await self._stack.aclose()
            raise McpConnectionError(
                f"Cannot connect to the MCP server: {e}") from e

    async def get_mcp_tool(self) -> Dict[str, ToolSpec]:
        """Return the tools exposed by the server, indexed by name."""
        mcp_tools: Dict[str, ToolSpec] = {}
        tools = await self._session.list_tools()
        for tool in tools.tools:
            mcp_tool = ToolSpec(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema
            )
            mcp_tools[tool.name] = mcp_tool
        return mcp_tools

    async def call_tool(self, name: str, arguments: Dict) -> str:
        """Call a tool and return its result as text.

        Text blocks are joined with newlines, other block types are
        replaced by a short "<type> omitted" notice.

        Args:
            name: Name of the tool to call.
            arguments: Arguments passed to the tool.

        Raises:
            McpToolError: If the server reports that the tool failed.
        """
        result = await self._session.call_tool(name, arguments)
        chunk = []
        for block in result.content:
            if block.type == "text":
                chunk.append(block.text)
            else:
                chunk.append(f"{block.type} omitted")
        text = "\n".join(chunk)
        if result.isError:
            raise McpToolError(text)
        return text

    async def close(self) -> None:
        """Close the MCP session and stop the server process."""
        await self._stack.aclose()
