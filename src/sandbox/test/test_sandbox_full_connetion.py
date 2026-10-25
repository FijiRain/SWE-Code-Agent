"""Full manual test script for the sandbox, MCP tools included.

Put it in `src/sandbox/test/` and run it from the project root, either by
calling main() from src/__main__.py or with:
    python -m src.sandbox.test.<name of this file without .py>

Each section prints the raw result, then a PASS/FAIL line for what the
sandbox must do. A summary is printed at the end, and the exit code is 1
if at least one check failed. It takes about a minute (timeout tests).

Things you may have to adapt:
- MCP_COMMAND: the command that starts the test MCP server.
- the config fields max_len_output / max_len_tool_output (see main()).
- the words looked for in the argument error messages (test_mcp_errors).
"""
import multiprocessing as mp
import os
import shlex
import socket
import subprocess
import sys
import threading
import time
from typing import List, Optional

from ..api import Sandbox
from ..ExecutionResult import ExecutionResult
from ..McpClient import McpConnectionError
from ..SandboxConfig import SandboxConfig, load_config

MCP_COMMAND = "python test/mcp_server_test.py"
CONFIG_PATH = "sandbox_template.json"

USE_COLOR = sys.stdout.isatty()  # no escape codes when output is redirected
GREEN = "\033[1;32m" if USE_COLOR else ""
RED = "\033[1;31m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""

RESULTS: List[bool] = []


def title(text: str) -> None:
    print(f"\n*** {text} ***")


def show(result: ExecutionResult) -> None:
    print(f"STDOUT: {result.stdout!r}")
    print(f"ERROR: {result.error!r}")
    print(f"TIMED_OUT: {result.timed_out} | TRUNCATED: {result.truncated} "
          f"| FINAL_ANSWER: {result.final_answer!r}")


def expect(label: str, condition: bool) -> None:
    RESULTS.append(condition)
    status = f"{GREEN}PASS{RESET}" if condition else f"{RED}FAIL{RESET}"
    print(f"[{status}] {label}")
    print("#" * 48)


def run(sand: Sandbox, code: str) -> ExecutionResult:
    """Execute code, print the raw result and return it."""
    result = sand.execute(code)
    show(result)
    return result


def summary() -> int:
    failed = RESULTS.count(False)
    passed = len(RESULTS) - failed
    color = GREEN if failed == 0 else RED
    print(f"\n{color}{passed}/{len(RESULTS)} checks passed{RESET}")
    return 1 if failed else 0


# --------------------------------------------------------------------------
# Sandbox restrictions
# --------------------------------------------------------------------------

def test_basics(sand: Sandbox) -> None:
    title("Basic Test")
    r = run(sand, "print('end')")
    expect("stdout is 'end' (no confusion with a protocol keyword)",
           r.stdout == "end\n" and r.error == "")

    title("Variable Persistence Test")
    sand.execute("x = 41")
    r = run(sand, "print(x + 1)")
    expect("x survives between two execute calls", r.stdout == "42\n")

    title("Class Definition Test")
    r = run(sand, "class A:\n    x = 1\nprint(A.x)")
    expect("class statement works", r.stdout == "1\n")


def test_final_answer(sand: Sandbox) -> None:
    title("Final Answer Test")
    r = run(sand, "print('a')\nfinal_answer('b')")
    expect("stdout is 'a' and final_answer is 'b'",
           r.stdout == "a\n" and r.final_answer == "b")

    title("Final Answer Swallowed By A Bare Except")
    r = run(sand, "try:\n    final_answer('b')\nexcept:\n    pass")
    expect("final_answer is still 'b'", r.final_answer == "b")

    title("Final Answer Reset Test")
    r = run(sand, "print('no answer here')")
    expect("final_answer is None again", r.final_answer is None)


def test_errors(sand: Sandbox) -> None:
    title("Python Error Test")
    r = run(sand, "1 / 0")
    expect("ZeroDivisionError is reported", "ZeroDivisionError" in r.error)
    r = run(sand, "print('alive')")
    expect("worker still alive after an error", r.stdout == "alive\n")

    title("Syntax Error Test")
    r = run(sand, "def (")
    expect("SyntaxError is reported", "SyntaxError" in r.error)

    title("SystemExit Test")
    sand.execute("x = 1")
    r = run(sand, "raise SystemExit")
    expect("message tells to use final_answer", "final_answer" in r.error)
    r = run(sand, "print(x)")
    expect("namespace survives SystemExit", r.stdout == "1\n")

    title("exit() Is Not Available Test")
    r = run(sand, "exit()")
    expect("exit is not defined (NameError)", "NameError" in r.error)

    title("KeyboardInterrupt Raised By The Code Test")
    r = run(sand, "raise KeyboardInterrupt")
    expect("reported as an error", "KeyboardInterrupt" in r.error)
    r = run(sand, "print('alive')")
    expect("worker still alive", r.stdout == "alive\n")


def test_imports(sand: Sandbox) -> None:
    title("Allowed Imports Test")
    r = run(sand, "import math\nprint(math.sqrt(4))")
    expect("import math works", r.stdout == "2.0\n")
    r = run(sand, "from collections import deque\nprint(len(deque([1, 2])))")
    expect("from-import works", r.stdout == "2\n")
    r = run(sand,
            "import collections.abc\nprint(collections.abc.Mapping.__name__)")
    expect("sub-module allowed by 'collections.*'", r.stdout == "Mapping\n")

    title("Refused Imports Test")
    for module in ("os", "sys", "subprocess", "socket"):
        r = run(sand, f"import {module}")
        expect(f"import {module} is refused", "ImportError" in r.error)

    title("Module Attribute Leaks Test")
    r = run(sand, "import collections\ncollections._sys")
    expect("private names are hidden", "AttributeError" in r.error)
    r = run(sand, "import typing\ntyping.sys")
    expect("unauthorized sub-modules are hidden",
           "AttributeError" in r.error)


def test_builtins(sand: Sandbox) -> None:
    title("Dangerous Builtins Test")
    for code in ("eval('1 + 1')", "exec('x = 1')",
                 "compile('1', 'f', 'eval')", "getattr(1, 'real')",
                 "input()"):
        r = run(sand, code)
        expect(f"{code} is blocked (NameError)", "NameError" in r.error)


def test_files(sand: Sandbox) -> None:
    title("Allowed Directory Test")
    r = run(sand,
            "with open('/tmp/agent/test.txt', 'w') as f:\n"
            "    f.write('hello')\n"
            "print(open('/tmp/agent/test.txt').read())")
    expect("write then read inside /tmp/agent", r.stdout == "hello\n")

    title("Forbidden Paths Test")
    for path in ("/etc/passwd", "/tmp/agent/../../etc/passwd",
                 "/tmp/agent2/x", "test.txt"):
        r = run(sand, f"open({path!r})")
        expect(f"{path} is refused", "PermissionError" in r.error)


def test_truncation(sand: Sandbox) -> None:
    title("Output Truncation Test")
    r = run(sand, "print('a' * 500)")
    expect("truncated flag and notice present",
           r.truncated and "[output truncated" in r.stdout)
    r = run(sand, "print('a' * 50)")
    expect("short output is untouched",
           not r.truncated and r.stdout == "a" * 50 + "\n")


def test_memory(sand: Sandbox) -> None:
    title("Memory Limit Test (Linux only)")
    r = run(sand, "x = bytearray(1024 * 1024 * 1024)")
    expect("1 GiB allocation fails (MemoryError or crash message)",
           r.error != "")
    r = run(sand, "print('alive')")
    expect("sandbox usable afterwards", r.stdout == "alive\n")

    title("Progressive Memory Growth Test (Linux only)")
    r = run(sand, "x = []\nwhile True:\n    x.append('a' * 10**6)")
    expect("stopped by the memory limit, not by the timeout",
           r.error != "" and not r.timed_out)
    r = run(sand, "print('alive')")
    expect("sandbox usable afterwards", r.stdout == "alive\n")


# --------------------------------------------------------------------------
# MCP tools (the test server exposes add, echo, run_tests, big_output,
# slow and fail)
# --------------------------------------------------------------------------

def test_mcp_tools(sand: Sandbox) -> None:
    title("MCP Tools Are In The Namespace")
    r = run(sand,
            "names = dir()\n"
            "print(all(n in names for n in ['add', 'echo', 'run_tests', "
            "'big_output', 'slow', 'fail']))")
    expect("the six tools exist", r.stdout == "True\n")

    title("Positional Arguments")
    r = run(sand, "print(add(1, 1))")
    expect("add(1, 1) gives 2", r.stdout == "2\n")

    title("Keyword Arguments")
    r = run(sand, "print(add(a=2, b=3))")
    expect("add(a=2, b=3) gives 5", r.stdout == "5\n")

    title("Text Argument")
    r = run(sand, "print(echo('hello'))")
    expect("echo returns its text", r.stdout == "hello\n")

    title("Tool Result Is A String")
    r = run(sand, "print(type(add(1, 1)).__name__)")
    expect("the result is a str", r.stdout == "str\n")

    title("Tool Call Between Two Prints")
    r = run(sand, "print('before')\nprint(add(1, 1))\nprint('after')")
    expect("stdout order is kept",
           r.stdout == "before\n2\nafter\n")

    title("Tool Calls In A Loop")
    r = run(sand,
            "total = 0\n"
            "for i in range(3):\n"
            "    total += int(add(i, i))\n"
            "print(total)")
    expect("0 + 2 + 4 = 6", r.stdout == "6\n")

    title("Many Tool Calls In A Row")
    r = run(sand, "print(sum(int(add(i, 1)) for i in range(20)))")
    expect("sum of 1..20 is 210 (messages stay in sync)",
           r.stdout == "210\n")

    title("Integer Given As A Float")
    r = run(sand, "print(add(2.0, 3))")
    expect("2.0 is accepted for an integer parameter", r.stdout == "5\n")

    title("run_tests With A Correct Solution")
    r = run(sand,
            "import json\n"
            "solution = 'def double(x):\\n    return x * 2'\n"
            "result = run_tests(solution, ['assert double(2) == 4'])\n"
            "print(json.loads(result)['success'])")
    expect("success is True", r.stdout == "True\n")

    title("run_tests With A Wrong Solution")
    r = run(sand,
            "import json\n"
            "solution = 'def double(x):\\n    return x * 2'\n"
            "result = run_tests(solution, ['assert double(2) == 5'])\n"
            "print(json.loads(result)['success'])")
    expect("success is False", r.stdout == "False\n")


def test_mcp_errors(sand: Sandbox) -> None:
    title("Missing Argument")
    r = run(sand, "add(1)")
    expect("refused, mentions the missing argument",
           "missing" in r.error.lower())

    title("Too Many Arguments")
    r = run(sand, "add(1, 2, 3)")
    expect("refused, mentions too many arguments",
           "too many" in r.error.lower())

    title("Argument Given Twice")
    r = run(sand, "add(1, a=1)")
    expect("refused, mentions multiple values",
           "multiple values" in r.error.lower())

    title("Unknown Argument Name")
    r = run(sand, "add(c=1)")
    expect("refused, mentions an invalid argument",
           "invalid argument" in r.error.lower()
           or "unexpected" in r.error.lower())

    title("Wrong Argument Type")
    r = run(sand, "add(1, '2')")
    expect("refused, mentions the expected type",
           "must be" in r.error.lower())

    title("Boolean Is Not An Integer")
    r = run(sand, "add(True, 1)")
    expect("refused", r.error != "")

    title("Tool That Fails")
    r = run(sand, "fail()")
    expect("the server message reaches the error field",
           "always fails" in r.error)
    r = run(sand, "print(echo('still ok'))")
    expect("worker and protocol still fine afterwards",
           r.stdout == "still ok\n")

    title("Tool Error Caught By The Code")
    r = run(sand,
            "try:\n"
            "    fail()\n"
            "except Exception:\n"
            "    print('caught')")
    expect("the code can catch it", r.stdout == "caught\n")

    title("Unknown Tool")
    r = run(sand, "inconnu()")
    expect("NameError", "NameError" in r.error)


def test_mcp_limits(sand: Sandbox) -> None:
    title("Tool Time Is Not Counted In The Timeout")
    r = run(sand, "print(slow(4))")
    expect("a 4 s tool succeeds with a 3 s timeout",
           "waited" in r.stdout and not r.timed_out)

    title("Timeout Still Works After A Slow Tool")
    r = run(sand, "slow(2)\nwhile True:\n    pass")
    expect("timed_out is True", r.timed_out)
    r = run(sand, "print(add(1, 1))")
    expect("tools work in the new worker", r.stdout == "2\n")

    title("Long Tool Output Is Truncated")
    r = run(sand,
            "text = big_output(2000)\n"
            "print(len(text), '[output truncated' in text)")
    parts = r.stdout.split()
    expect("the value received by the code is cut and has a notice, "
           "and truncated is True",
           len(parts) == 2 and parts[0].isdigit() and int(parts[0]) < 2000
           and parts[1] == "True" and r.truncated)

    title("Short Tool Output Is Untouched")
    r = run(sand, "print(len(big_output(100)))")
    expect("100 characters, not truncated",
           r.stdout == "100\n" and not r.truncated)


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------

def test_timeouts(sand: Sandbox) -> None:
    title("Time Out With Partial Output Test")
    r = run(sand, "print('a')\nprint('b')\nwhile True:\n    pass")
    expect("timed_out is True and stdout is 'a\\nb\\n'",
           r.timed_out and r.stdout == "a\nb\n")

    title("Time Out Alone Test")
    r = run(sand, "while True:\n    pass")
    expect("timed_out is True and stdout is empty",
           r.timed_out and r.stdout == "")

    title("Time Out With Endless Output Test")
    r = run(sand, "while True:\n    print('x')")
    expect("timed_out is True and output is truncated",
           r.timed_out and r.truncated)

    title("Consecutive Timeouts Test")
    for _ in range(3):
        r = sand.execute("while True:\n    pass")
    show(r)
    expect("third timeout is handled", r.timed_out)
    r = run(sand, "print('after')")
    expect("worker usable after the timeouts", r.stdout == "after\n")
    r = run(sand, "print(add(1, 1))")
    expect("MCP tools usable after the timeouts", r.stdout == "2\n")
    expect("exactly one worker alive (no zombies)",
           len(mp.active_children()) == 1)


# --------------------------------------------------------------------------
# Sandboxes with a special configuration
# --------------------------------------------------------------------------

def test_crash(config: SandboxConfig) -> None:
    # os is allowed here only to be able to kill the worker on purpose.
    # (os._exit is hidden by the "_" filter, so we use os.kill instead.)
    crash_config = config.model_copy(update={
        "authorized_imports": config.authorized_imports + ["os"],
    })
    sand = Sandbox(MCP_COMMAND, crash_config)
    try:
        title("Crash Test")
        run(sand, "x = 1")
        r = run(sand, "import os\nos.kill(os.getpid(), 9)")
        expect("crash message returned, no exception raised",
               "crashed" in r.error)
        r = run(sand, "print(x)")
        expect("variables are lost after the restart (NameError)",
               "NameError" in r.error)
        r = run(sand, "print(add(1, 1))")
        expect("MCP tools still work in the new worker",
               r.stdout == "2\n")
    finally:
        sand.close()


def test_network(config: SandboxConfig) -> None:
    # socket is allowed here so that only the network block protects us.
    net_config = config.model_copy(update={
        "authorized_imports": config.authorized_imports + ["socket"],
    })
    sand = Sandbox(MCP_COMMAND, net_config)
    try:
        title("Network Blocked Even If socket Is Allowed Test")
        for code in (
            "import socket\nsocket.socket()",
            "import socket\nsocket.create_connection(('example.com', 80))",
            "import socket\nsocket.getaddrinfo('example.com', 80)",
        ):
            r = run(sand, code)
            expect(f"{code.splitlines()[1]} is refused",
                   "PermissionError" in r.error)
        r = run(sand, "print(1)")
        expect("pipe still works after the network block",
               r.stdout == "1\n")
        r = run(sand, "print(add(1, 1))")
        expect("MCP tools work although the worker has no network",
               r.stdout == "2\n")

        title("Main Process Network Untouched Test")
        try:
            socket.socket().close()
            untouched = True
        except Exception:
            untouched = False
        expect("main process can still create sockets", untouched)
    finally:
        sand.close()


# --------------------------------------------------------------------------
# Life cycle
# --------------------------------------------------------------------------

def test_lifecycle(config: SandboxConfig) -> None:
    title("Default Configuration")
    sand = Sandbox(MCP_COMMAND)
    try:
        r = run(sand, "print(add(1, 1))")
        expect("works with the default SandboxConfig", r.stdout == "2\n")
    finally:
        sand.close()

    title("MCP Command Is Required")
    try:
        Sandbox()  # type: ignore[call-arg]
        required = False
    except TypeError as e:
        print(f"Raised TypeError: {e}")
        required = True
    expect("Sandbox() without a command raises TypeError", required)

    title("Unknown MCP Command")
    threads_before = threading.active_count()
    raised: Optional[BaseException] = None
    try:
        Sandbox("doesnotexist", config)
    except Exception as e:
        raised = e
        print(f"Raised {type(e).__name__}: {e}")
    expect("McpConnectionError is raised",
           isinstance(raised, McpConnectionError))
    expect("no thread left behind",
           threading.active_count() == threads_before)
    expect("no worker left behind", len(mp.active_children()) == 0)

    title("MCP Script Not Found")
    threads_before = threading.active_count()
    raised = None
    try:
        Sandbox("python test/this_script_does_not_exist.py", config)
    except Exception as e:
        raised = e
        print(f"Raised {type(e).__name__}: {e}")
    expect("McpConnectionError is raised",
           isinstance(raised, McpConnectionError))
    expect("the message names the missing script",
           raised is not None and "this_script_does_not_exist" in str(raised))
    expect("no thread left behind",
           threading.active_count() == threads_before)
    expect("no worker left behind", len(mp.active_children()) == 0)

    title("MCP Process That Never Answers (takes about 15 s)")
    start = time.monotonic()
    raised = None
    try:
        Sandbox('python -c "import time; time.sleep(60)"', config)
    except Exception as e:
        raised = e
        print(f"Raised {type(e).__name__}: {e}")
    elapsed = time.monotonic() - start
    expect(f"fails with an exception after {elapsed:.0f} s (< 30 s)",
           raised is not None and elapsed < 30)

    title("Close Twice")
    sand = Sandbox(MCP_COMMAND, config)
    sand.close()
    try:
        sand.close()
        second_close_ok = True
    except Exception as e:
        print(f"Raised {type(e).__name__}: {e}")
        second_close_ok = False
    expect("the second close() does nothing", second_close_ok)


def server_processes_left() -> Optional[bool]:
    """True if a process of the test MCP server is still running."""
    script = shlex.split(MCP_COMMAND)[-1]
    try:
        result = subprocess.run(["pgrep", "-f", script],
                                capture_output=True)
    except FileNotFoundError:
        return None
    return result.returncode == 0


def test_no_leftovers() -> None:
    title("No Process Left Behind")
    time.sleep(1)   # let the processes finish
    expect("no multiprocessing worker alive", len(mp.active_children()) == 0)
    left = server_processes_left()
    if left is None:
        print("pgrep is not available: server check skipped")
    else:
        expect("no MCP server process left", not left)


def main() -> int:
    base = load_config(CONFIG_PATH)
    config = base.model_copy(update={
        "max_execution_time_seconds": 3,   # keep timeout tests fast
        "max_len_output": 200,             # small limit to test truncation
        "max_len_tool_output": 500,        # same, for tool results
    })
    os.makedirs("/tmp/agent", exist_ok=True)

    sand = Sandbox(MCP_COMMAND, config)
    try:
        test_basics(sand)
        test_final_answer(sand)
        test_errors(sand)
        test_imports(sand)
        test_builtins(sand)
        test_files(sand)
        test_truncation(sand)
        test_mcp_tools(sand)
        test_mcp_errors(sand)
        test_mcp_limits(sand)
        test_memory(sand)
        test_timeouts(sand)
    finally:
        sand.close()

    test_crash(config)
    test_network(config)
    test_lifecycle(config)
    test_no_leftovers()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
