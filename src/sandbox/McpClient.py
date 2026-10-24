import shlex
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Dict
from contextlib import AsyncExitStack
from pydantic import BaseModel, Field
import asyncio


class ToolSpec(BaseModel):
    name: str = Field(
        ...,
        description="name of tool"
    )
    description: str = Field(
        default="",
        description="Description of tool"
    )
    input_schema: dict = Field(
        default_factory={},
        description="Argument of tool"
    )


class McpToolError(Exception):
    """Raised when an MCP tool reports an error."""


class McpConnectionError(Exception):
    """Raised when the MCP server cannot be reached or initialized."""


class McpClient:
    def __init__(self, command: str):
        parts = shlex.split(command)
        if not parts:
            raise ValueError("Empty MCP Server command")
        self._params = StdioServerParameters(
            command=parts[0],
            args=parts[1:]
        )

    async def connect(self) -> None:
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
        mcp_tools: Dict[ToolSpec] = {}
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
        await self._stack.aclose()
