from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config


def main() -> None:
    sand = Sandbox(load_config("sandbox_template.json"))

    result = sand.execute("print('hello world')")
    print(f"Output: {result.stdout}")
    print(f"ExectutionResult: {result}")

    sand.close()


if __name__ == "__main__":
    main()
