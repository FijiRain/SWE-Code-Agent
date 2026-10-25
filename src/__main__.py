from .sandbox.test.test_sandbox_full_connetion import main


def missing_server_test():
    from .sandbox.api import Sandbox
    try:
        sand = Sandbox("python src/sandbox/test/mcp_server_test.pya")
    except Exception as e:
        print(f"{type(e).__name__}: {e}")
        return
    sand.execute("print('a')")


if __name__ == "__main__":
    # missing_server_test()
    main()
