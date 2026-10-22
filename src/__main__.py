# import asyncio
# import sys

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client


# async def mcp_clien() -> None:
#     params = StdioServerParameters(
#         command=sys.executable,
#         args=["test/mcp_server_test.py"]
#     )
#     async with stdio_client(params) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()

#             # tools = await session.list_tools()
#             # for tool in tools.tools:
#             #     print(f"{tool.name}: {tool.description}")
#             #     print(f"{tool.inputSchema}")

#             result = await session.call_tool("add", {"a": 1, "b": 'z'})
#             for block in result.content:
#                 if block.type == "text":
#                     print(block.text)

# asyncio.run(mcp_clien())

from .sandbox.McpClient import McpClient, McpToolError, McpConnectionError
import asyncio


async def test_client():
    client = McpClient("python test/mcp_server_test.py")
    try:
        await client.connect()
    except McpConnectionError as e:
        print(f"Connection failed: {e}")
        return
    try:
        print(await client.get_mcp_tool())
        print(await client.call_tool("slow", {"seconds": 15}))
        print(await client.call_tool("add", {"a": 1, "b": 1}))
        print(await client.call_tool("fail", {}))

    except McpToolError as e:
        print(e)
    finally:
        await client.close()


def main():
    asyncio.run(test_client())


if __name__ == "__main__":
    main()
