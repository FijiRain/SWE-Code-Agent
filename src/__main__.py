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

# from .sandbox.McpClient import McpClient, McpToolError, McpConnectionError
# import asyncio


# async def test_client():
#     client = McpClient("python test/mcp_server_test.py")
#     try:
#         await client.connect()
#     except McpConnectionError as e:
#         print(f"Connection failed: {e}")
#         return
#     try:
#         tools = await client.get_mcp_tool()
#         print(tools["add"].input_schema)
#         print("\n".join(tools["add"].input_schema))
#         names = list(tools["add"].input_schema.get("properties", {}))
#         required = tools["add"].input_schema.get("required", [])
#         print(names)
#         print(required)
#         print(tools["add"].input_schema["properties"][names[0]]["type"])
#         # print(type(await client.get_mcp_tool()))
#         # print(await client.call_tool("slow", {"seconds": 15}))
#         # print(await client.call_tool("add", {"a": 1, "b": 1}))
#         # print(await client.call_tool("fail", {}))

#     except McpToolError as e:
#         print(e)
#     finally:
#         await client.close()

# from .sandbox.McpBrige import McpBridge


# def main():
#     bridge = McpBridge("python test/mcp_server_test.py")
#     bridge.connect()
#     print(bridge.call_tool("add", {'a': 1, 'b': 1}))
#     bridge.close()
#     # asyncio.run(test_client())




# if __name__ == "__main__":
    # main()
    # asyncio.run(test_client())


from .sandbox.McpClient import ToolSpec
from .sandbox.wrapper_tools import WorkerToolMessageIntput, make_tools_wrapper

spec = ToolSpec(name="add", input_schema={
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
})


class FakeConn:
    def send(self, msg):
        print("sent:", msg)

    def recv(self):
        return ("tool_result", WorkerToolMessageIntput(output="2"))


add = make_tools_wrapper(spec, FakeConn())
print(add(1, 1))      # "sent: ..." then 2
print(add(a=1, b=1))  # same

print("****************************")
print("missing b")
try:
    add(1)
except TypeError as e:
    print(e)            # error: missing b
print()
print("error: too many arguments")
try:
    add(1, 2, 3)       # error: too many arguments
except TypeError as e:
    print(e)
print()
print("error: multiple values for 'a'")
try:
    add(1, a=1)       # error: multiple values for 'a'
except TypeError as e:
    print(e)
print()
print("error: b must be integer")
try:
    add(1, "2")       # error: b must be integer
except TypeError as e:
    print(e)
print()
print("error: invalid argument")
try:
    add(c=1)      # error: invalid argument
except TypeError as e:
    print(e)
