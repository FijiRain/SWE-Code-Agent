from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config


def main():
    sand = Sandbox(load_config("sandbox_template.json"))

    print("\n*** Basic Test ***")
    result = sand.execute("print('end')")
    print(f"STDOUT: {result.stdout}")
    print("################################################")

    print("\n*** Final Answer Test ***")
    result = sand.execute("print('a')")
    print(f"STDOUT: {result.stdout}")
    result = sand.execute("final_answer('b')")
    print(f"FINAL_ANSWER: {result.final_answer}")
    print("################################################")

    print("\n*** Python Error ***")
    result = sand.execute("1 / 0")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print("################################################")

    print("\n*** Time Out Test ***")
    result = sand.execute("print('a')\nprint('b')\nwhile True:\n\tpass")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print(f"TIMED_OUT: {result.timed_out}")
    print("################################################")

    print("\n*** Time Out Alone Test")
    result = sand.execute("while True:\n\tpass")
    print(f"ERROR: {result.error}")
    print(f"TIMED_OUT: {result.timed_out}")
    print("################################################")

    print("\n*** Crash Test ***")
    result = sand.execute("x = 1\nimport os; os.exit(1)\nprint(x)")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print("################################################")

    print("\n*** Exit Test ***")
    result = sand.execute("x = 1\nexit()")
    print(f"ERROR: {result.error}")
    result = sand.execute("print(x)")
    print(f"STDOUT: {result.stdout}")
    print("################################################")

    print("\n*** Consecutive Timeout Test ***")
    result = sand.execute("while True:\n\tpass")
    result = sand.execute("while True:\n\tpass")
    result = sand.execute("while True:\n\tpass")
    print(f"TIMED_OUT: {result.timed_out}")
    print("Run `ps` to ensure that all workers have been properly shut down.")

    sand.close()


if __name__ == "__main__":
    main()
