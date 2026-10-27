"""Command line entry point of the interactive sandbox."""
from .config import RED, RESET
from .repl import repl
from .api import Sandbox
from .McpClient import McpConnectionError
from ..models.SandboxConfig import load_config

import argparse
import sys


def main() -> int:
    """Parse the arguments, start the sandbox and run the REPL.

    Returns:
        The exit code: 0 on success, 1 if the configuration or the MCP
        connection is invalid, 130 on KeyboardInterrupt.
    """
    parser = argparse.ArgumentParser(
        description="Launche the intercative sandbox"
    )
    parser.add_argument(
        "config",
        nargs='?',
        default=None,
        help="path to config file"
    )
    mcp_group = parser.add_mutually_exclusive_group()
    mcp_group.add_argument(
        "--mcp-stdio",
        type=str,
        default=None,
        help="Command to launch MCP server over stdio"
    )
    mcp_group.add_argument(
        "--mcp-server",
        type=str,
        default=None,
        help="Url of MCP server"
    )

    args = parser.parse_args()

    config = args.config
    if config is not None:
        try:
            config = load_config(config)
        except (ValueError, RuntimeError) as e:
            print(f"{RED}Invalid configuration: {e}{RESET}", file=sys.stderr)
            return 1
    mcp_connection = args.mcp_stdio or args.mcp_server

    try:
        with Sandbox(mcp_connection, config, True) as sandbox:
            repl(sandbox)
    except McpConnectionError as e:
        print(f"{RED}Cannot start the sandbox: {e}{RESET}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
