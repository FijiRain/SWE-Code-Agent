import argparse
import sys
from mcp.server.fastmcp import FastMCP
from src.tools.filesystem import read_file, edit_file, list_files
from src.tools.search import (search_code,
                              search_function_or_class_definition_in_code,
                              find_references)
from src.tools.execution import (run_swebench_tests as run_tests,
                                 get_patch, run_command)


mcp = FastMCP("swebench_tools")
tools = [
    read_file,
    edit_file,
    list_files,
    search_code,
    search_function_or_class_definition_in_code,
    find_references,
    get_patch,
    run_command,
]

for tool in tools:
    mcp.tool()(tool)
mcp.tool(name="run_tests")(run_tests)


def main():
    """Parse command-line arguments and run the SWE-bench MCP server.

    Configures the transport protocol (stdio or SSE/HTTP) and network
    settings before starting the server.
    """
    parser = argparse.ArgumentParser(description="SWE-bench MCP Server")
    parser.add_argument(
            "--transport",
            choices=["stdio", "sse", "http"],
            default="stdio",
            help="Transport type (stdio or sse/http)")
    parser.add_argument("--port", type=int, default=8001,
                        help="Port for SSE/HTTP transport")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host for SSE/HTTP transport")

    args = parser.parse_args()
    transport = "sse" if args.transport in ["http", "sse"] else "stdio"

    if transport == "sse":
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        print("Starting SWE-bench MCP Server on "
              f"http://{args.host}:{args.port}/sse", file=sys.stderr)

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
