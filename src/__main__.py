from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config


def main():
    sand = Sandbox(load_config("sandbox_template.json"))

    result = sand.execute("import os;os._exit(1)")
    print(result.error, end="")
    sand.close()
    # result = sand.execute("print(1/ 0)")
    # print(result.error)
    # result = sand.execute("final_answer('b')")
    # print(result.final_answer)


if __name__ == "__main__":
    main()
