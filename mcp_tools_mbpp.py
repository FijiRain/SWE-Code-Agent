from src.tools.execution import run_mbpp_tests as run_tests
from mcp.server.fastmcp import FastMCP
from typing import Literal
import argparse
import sys


# Initialize and register at module level so any test or client can import mcp
# directly if needed (from mcp_tools_mbpp import mcp).
mcp = FastMCP("mbpp_tools")
mcp.tool(name="run_tests")(run_tests)


def main() -> None:
    """Parse command-line arguments and run the MBPP MCP server.

    Configures the transport protocol (stdio or SSE/HTTP) and network
    settings before starting the server.
    """
    parser = argparse.ArgumentParser(description="MBPP MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport type (stdio or sse/http)")

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["stdio", "http"],
        default=None,
        help="Optional positional transport mode (stdio or http)")

    parser.add_argument("--port", type=int, default=8000,
                        help="Port for SSE/HTTP transport")

    parser.add_argument("--host", default="127.0.0.1",
                        help="Host for SSE/HTTP transport")

    args = parser.parse_args()
    selected_mode = args.mode or args.transport
    transport: Literal["stdio", "streamable-http"] = (
        "streamable-http"
        if selected_mode in ["http", "sse", "streamable-http"]
        else "stdio"
    )

    if transport == "streamable-http":
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        print("Starting MBPP MCP Server on "
              f"http://{args.host}:{args.port}/mcp", file=sys.stderr)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
