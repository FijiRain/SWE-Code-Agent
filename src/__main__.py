from .sandbox.test.test_sandbox_full_connetion import main


def missing_server_test():
    from .sandbox.api import Sandbox

    sand = Sandbox("un trunc null")
    sand.execute("print('a')")


if __name__ == "__main__":
    missing_server_test()
    # main()
