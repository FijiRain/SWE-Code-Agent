"""Entry point of the project: run the sandbox test script."""
# from .sandbox.test.test_sandbox_full_connetion import main


from .sandbox.api import Sandbox
import sys


def main() -> int:
    """Run the interactive sandbox and return its exit code."""
    # from .sandbox.test.sandbox_full_test import main
    # Sandbox("python mcp_tools_swebench.py --container smith-ID", config,
    #     mcp_env={"TESTBED_PATH": host_dir})
    # main()
    # return sandbox_cli()

    with Sandbox("python src/sandbox/test/mcp_server_test.py") as sand:
        print(sand.execute("print(get_env('PATH'))"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
