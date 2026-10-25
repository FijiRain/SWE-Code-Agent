"""Asynchronous MCP client that talks to a server started over stdio."""
import shlex
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Dict, List
from contextlib import AsyncExitStack
from pydantic import BaseModel, Field
import asyncio
import os
import sys
import shutil


class ToolSpec(BaseModel):
    """Description of one tool exposed by the MCP server."""

    name: str = Field(
        ...,
        description="name of tool"
    )
    description: str = Field(
        default="",
        description="Description of tool"
    )
    input_schema: dict = Field(
        default_factory=dict,
        description="Argument of tool"
    )


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
    """Client of an MCP server launched as a subprocess over stdio."""

    def __init__(self, command: str):
        """Parse and check the command that starts the MCP server.

        Args:
            command: Shell-like command line that starts the server.

        Raises:
            McpConnectionError: If the command is invalid or not runnable.
            ValueError: If the command is empty.
        """
        try:
            parts = shlex.split(command)
        except ValueError as e:
            raise McpConnectionError(f"Invalid MCP server command: {e}") from e
        if not parts:
            raise ValueError("Empty MCP Server command")
        check_server_command(parts)
        self._params = StdioServerParameters(
            command=parts[0],
            args=parts[1:]
        )

    async def connect(self) -> None:
        """Start the server and initialize the MCP session.

        Raises:
            McpConnectionError: If the server cannot be started or does not
                finish initialization within 10 seconds.
        """
        self._stack = AsyncExitStack()
        try:
            read, write = await self._stack.enter_async_context(
                stdio_client(self._params)
                )
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

    async def close(self):
        """Close the MCP session and stop the server process."""
        await self._stack.aclose()
