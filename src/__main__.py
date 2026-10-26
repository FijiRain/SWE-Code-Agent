from .sandbox.test.test_sandbox_full_connetion import main

def test_manual():
    from .sandbox.api import Sandbox

    sand = Sandbox("python src/sandbox/test/mcp_server_test.py")
    print(sand.get_manual())


if __name__ == "__main__":
    main()
    # test_manual()
