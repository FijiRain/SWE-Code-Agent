"""Entry point of the project: run the sandbox test script."""
# from .sandbox.test.test_sandbox_full_connetion import main
from .sandbox.repl import repl
from .sandbox.api import Sandbox
from .sandbox.repl import RED, RESET
from .sandbox.McpClient import McpConnectionError
import sys


def test_manual() -> None:
    """Start a sandbox on the test MCP server and print its manual."""
    from .sandbox.api import Sandbox

    sand = Sandbox("python src/sandbox/test/mcp_server_test.py")
    print(sand.get_manual())


def main() -> int:
    try:
        with Sandbox("http://127.0.0.1:8000/mcp", None, True) as sandbox:
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
