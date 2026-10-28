"""Entry point of the project: run the sandbox test script."""
# from .sandbox.test.test_sandbox_full_connetion import main
from .sandbox.cli import main as sandbox_cli
import sys


def test_manual() -> None:
    """Start a sandbox on the test MCP server and print its manual."""
    from .sandbox.api import Sandbox

    sand = Sandbox("python src/sandbox/test/mcp_server_test.py")
    print(sand.get_manual())


def main() -> int:
    """Run the interactive sandbox and return its exit code."""
    return sandbox_cli()


if __name__ == "__main__":
    sys.exit(main())
