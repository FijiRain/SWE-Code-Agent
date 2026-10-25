"""Mini MCP server, only to test the sandbox client.

It is NOT the real server of the project
(mcp_tools_mbpp.py /mcp_tools_swebench.py).
It exposes a few tools with different kinds of parameters and results, one
resource and one prompt.

Run it:
    python mini_mcp_server.py          # stdio (the client launches it)
    python mini_mcp_server.py http
    # streamable HTTP (default: http://127.0.0.1:8000/mcp)

Warning: with stdio, never print() to stdout in this file, it would corrupt
the protocol. Use stderr if you need to debug.
"""
import json
import sys
import time

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mini-test-server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.tool()
def add_tree_nb(a: int, b: int, c: int) -> int:
    """Add tree integers."""
    return a + b + c


@mcp.tool()
def echo(text: str) -> str:
    """Return the given text unchanged."""
    return text


@mcp.tool()
def run_tests(code: str, test_list: list[str]) -> str:
    """Run a candidate solution against the given test assertions.

    Returns a JSON string with a boolean 'success' and an 'output' field.
    (Test server only: it runs the code with exec, without any sandbox.)
    """
    namespace: dict = {}
    try:
        exec(code, namespace)
        for test in test_list:
            exec(test, namespace)
    except Exception as e:
        return json.dumps({"success": False,
                           "output": f"{type(e).__name__}: {e}"})
    return json.dumps({"success": True, "output": "all tests passed"})


@mcp.tool()
def big_output(size: int) -> str:
    """Return a string of 'size' characters (to test output truncation)."""
    return "a" * size


@mcp.tool()
def slow(seconds: float) -> str:
    """Wait for 'seconds' seconds (to test that tool time is not timed out)."""
    time.sleep(seconds)
    return f"waited {seconds}s"


@mcp.tool()
def fail() -> str:
    """Always raise an error (to test error handling)."""
    raise ValueError("this tool always fails")


@mcp.resource("demo://greeting")
def greeting() -> str:
    """A small text resource."""
    return "Hello from the mini MCP server"


@mcp.prompt()
def review_code(code: str) -> str:
    """A small prompt template."""
    return f"Please review this code:\n\n{code}"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()