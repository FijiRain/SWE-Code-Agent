from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config


def test_timout() -> None:
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


def test_import_and_builtins() -> None:
    sand = Sandbox(load_config("sandbox_template.json"))

    print("\n*** Basic Test ***")
    print("################################################")
    result = sand.execute("print('a')")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Import Math Test ***")
    print("################################################")
    result = sand.execute(
        """
import math
print(math.sqrt(4))
    """)
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Import OS Test ***")
    print("################################################")
    result = sand.execute("import os")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Import Typing Test ***")
    print("################################################")
    result = sand.execute("import typing")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Import typing.sys Test ***")
    print("################################################")
    result = sand.execute("import typing.sys")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Import typing.io Test ***")
    print("################################################")
    result = sand.execute("import typing.io")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** From Typing Import List Test ***")
    print("################################################")
    result = sand.execute("from typing import List")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Collections ABC Test ***")
    print("################################################")
    result = sand.execute("""
import collections.abc

collections.abc.Mapping
    """)
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Open Test ***")
    print("################################################")
    result = sand.execute("open('x')")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Eval Test ***")
    print("################################################")
    result = sand.execute("eval('1')")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Getattr Test ***")
    print("################################################")
    result = sand.execute("getattr(1, 'real')")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Class Definition Test ***")
    print("################################################")
    result = sand.execute("class A: pass\nprint(A)")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    print("\n*** Assertion Test ***")
    print("################################################")
    result = sand.execute("assert 1 == 2")
    print(f"STDOUT: {result.stdout}")
    print(f"ERROR: {result.error}")
    print()

    sand.close()


def main():
    test_timout()


if __name__ == "__main__":
    main()
