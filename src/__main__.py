"""Entry point of the project: run the sandbox test script."""
from .sandbox.test.test_sandbox_full_connetion import main
from .sandbox.repl import repl


def test_manual() -> None:
    """Start a sandbox on the test MCP server and print its manual."""
    from .sandbox.api import Sandbox

    sand = Sandbox("python src/sandbox/test/mcp_server_test.py")
    print(sand.get_manual())


if __name__ == "__main__":
    # main()
    repl("python src/sandbox/test/mcp_server_test.py")
    # test_manual()
