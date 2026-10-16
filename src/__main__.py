from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config


def main():
    sand = Sandbox(load_config("sandbox_template.json"))

    result = sand.execute("print('before')")
    print(result.stdout, end="")
    # result = sand.execute('while True:\n\tpass')
    # print(result.error, end="")
    # print()
    # print(result.timed_out)
    # print()
    # result = sand.execute("print('after')")
    # print(result.stdout, end="")
    sand.close()
    # result = sand.execute("print(1/ 0)")
    # print(result.error)
    # result = sand.execute("final_answer('b')")
    # print(result.final_answer)


if __name__ == "__main__":
    main()
