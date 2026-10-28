"""Full manual test script for the sandbox (tools, manual, HTTP, REPL, CLI).

Put it in `src/sandbox/test/`, next to `mcp_server_test.py`, and run it from
the project root, either by calling main() from src/__main__.py or with:
    python -m src.sandbox.test.<name of this file without .py>

Each section prints the raw result, then a PASS/FAIL line for what the
sandbox must do. A summary is printed at the end, and the exit code is 1
if at least one check failed. An unexpected exception in a section is
reported as a failure and does not stop the other sections.

Options (read from sys.argv):
    --quick    skip the slowest sections (about 2 minutes instead of 3-4)

Things this script assumes (a section fails if the feature is missing):
- the test MCP server is in the same folder as this file and understands
  the argument `http` to run over streamable HTTP on port 8000;
- Sandbox(mcp_command, sandbox_config=None, echo=False): mcp_command may be
  None (no tool), and echo can be given as a keyword;
- SandboxConfig has max_len_output and max_len_tool_output;
- the REPL module exposes is_complete (or the old name is_complet);
- the `sandbox` command is installed (run through `uv run`) for the CLI tests.
"""
import multiprocessing as mp
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import List, Optional, Set

from ..api import Sandbox
from ...models.ExecutionResult import ExecutionResult
from ..McpClient import McpConnectionError
from ...models.SandboxConfig import SandboxConfig, load_config

from ..repl import is_complet as is_complete

SERVER_SCRIPT = Path(__file__).with_name("mcp_server_test.py")
MCP_COMMAND = f"{shlex.quote(sys.executable)} {shlex.quote(str(SERVER_SCRIPT))}"
HTTP_PORT = 8000
HTTP_URL = f"http://127.0.0.1:{HTTP_PORT}/mcp"
CONFIG_PATH = "sandbox_template.json"
TOOL_NAMES = ["add", "echo", "run_tests", "big_output", "slow", "fail"]

QUICK = "--quick" in sys.argv

USE_COLOR = sys.stdout.isatty()  # no escape codes when output is redirected
GREEN = "\033[1;32m" if USE_COLOR else ""
RED = "\033[1;31m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""

RESULTS: List[bool] = []
FAILURES: List[str] = []
CURRENT_TITLE = ""
BASELINE_SERVER_PIDS: Set[str] = set()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def title(text: str) -> None:
    global CURRENT_TITLE
    CURRENT_TITLE = text
    print(f"\n*** {text} ***")


def show(result: ExecutionResult) -> None:
    print(f"STDOUT: {result.stdout!r}")
    print(f"ERROR: {result.error!r}")
    print(f"TIMED_OUT: {result.timed_out} | TRUNCATED: {result.truncated} "
          f"| FINAL_ANSWER: {result.final_answer!r}")


def expect(label: str, condition: bool) -> None:
    RESULTS.append(condition)
    if not condition:
        FAILURES.append(f"{CURRENT_TITLE}: {label}")
    status = f"{GREEN}PASS{RESET}" if condition else f"{RED}FAIL{RESET}"
    print(f"[{status}] {label}")
    print("#" * 48)


def run(sand: Sandbox, code: str) -> ExecutionResult:
    """Execute code, print the raw result and return it."""
    result = sand.execute(code)
    show(result)
    return result


def attempt(test, *args) -> None:
    """Run one test function; an unexpected exception counts as a failure."""
    try:
        test(*args)
    except Exception:
        traceback.print_exc()
        expect(f"{test.__name__} ran without an unexpected exception", False)


def summary() -> int:
    failed = RESULTS.count(False)
    passed = len(RESULTS) - failed
    color = GREEN if failed == 0 else RED
    if FAILURES:
        print(f"\n{RED}Failed checks, by section:{RESET}")
        for failure in FAILURES:
            print(f"  - {failure}")
    print(f"\n{color}{passed}/{len(RESULTS)} checks passed{RESET}")
    return 1 if failed else 0


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_is_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def wait_for_port(port: int, timeout: float = 10) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_http_server() -> Optional[subprocess.Popen]:
    """Start the test MCP server over HTTP. None if it cannot be started."""
    if not port_is_free(HTTP_PORT):
        print(f"Port {HTTP_PORT} is already in use: HTTP sections skipped")
        return None
    process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT), "http"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if not wait_for_port(HTTP_PORT):
        process.kill()
        process.wait()
        print("The HTTP server did not start: HTTP sections skipped")
        return None
    return process


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def server_pids() -> Optional[Set[str]]:
    """PIDs of the running test MCP servers (None if pgrep is missing)."""
    try:
        result = subprocess.run(["pgrep", "-f", SERVER_SCRIPT.name],
                                capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return set(result.stdout.split())


def server_processes_left() -> Optional[bool]:
    """True if a server started during this run is still running.

    Servers that were already running when the script started (for example
    one started by hand for the HTTP tests) are ignored.
    """
    pids = server_pids()
    if pids is None:
        return None
    return bool(pids - BASELINE_SERVER_PIDS)


def expect_connection_error(target: str, config: SandboxConfig,
                            max_seconds: float,
                            mention: Optional[str] = None) -> None:
    """Sandbox(target) must raise McpConnectionError, fast, and clean up."""
    threads_before = threading.active_count()
    start = time.monotonic()
    raised: Optional[BaseException] = None
    try:
        sand = Sandbox(target, config)
    except Exception as e:
        raised = e
        print(f"Raised {type(e).__name__}: {e}")
    else:
        sand.close()
    elapsed = time.monotonic() - start
    expect("McpConnectionError is raised",
           isinstance(raised, McpConnectionError))
    if mention:
        expect(f"the message mentions '{mention}'",
               raised is not None and mention in str(raised).lower())
    expect(f"fails within {max_seconds:.0f} s ({elapsed:.1f} s)",
           elapsed < max_seconds)
    expect("no thread left behind",
           threading.active_count() == threads_before)
    expect("no worker left behind", len(mp.active_children()) == 0)


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

    title("Expression Value Is Not Echoed By Default")
    r = run(sand, "1 + 1")
    expect("no output for a bare expression", r.stdout == "")


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
            f"print(all(n in names for n in {TOOL_NAMES!r}))")
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
    expect("stdout order is kept", r.stdout == "before\n2\nafter\n")

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
# Manual and tool_help
# --------------------------------------------------------------------------

def test_manual(sand: Sandbox) -> None:
    title("Manual With Tools")
    manual = sand.get_manual()
    print(manual)
    print(f"\nSize: {len(manual)} characters (about {len(manual) // 4} tokens)")
    expect("no placeholder left", "$" not in manual)
    expect("every tool appears in the manual",
           all(name in manual for name in TOOL_NAMES))
    expect("final_answer is documented", "final_answer" in manual)
    expect("tool_help is documented", "tool_help" in manual)
    expect("the forbidden functions are listed", "eval" in manual)

    title("The Example Of The Manual Runs")
    example = next((line for line in manual.splitlines()
                    if line.startswith("print(tool_help(")), None)
    if example is None:
        expect("the manual contains a tool_help example", False)
    else:
        r = run(sand, example)
        expect("the example gives a result and no error",
               r.error == "" and r.stdout != "")


def test_manual_follows_config(config: SandboxConfig) -> None:
    title("Manual Follows The Configuration")
    custom = config.model_copy(update={
        "max_execution_time_seconds": 17,
        "max_memory_mb": 321,
    })
    with Sandbox(MCP_COMMAND, custom) as sand:
        manual = sand.get_manual()
    expect("17 s and 321 MB appear in the manual",
           "17" in manual and "321" in manual)


def test_tool_help(sand: Sandbox) -> None:
    title("tool_help With One Tool")
    r = run(sand, "print(tool_help(['add']))")
    expect("prototype and parameters are given",
           "add(a: int, b: int)" in r.stdout and "Parameters:" in r.stdout)

    title("tool_help With Several Tools")
    r = run(sand,
            "text = tool_help(['add', 'echo'])\n"
            "print('add(a: int, b: int)' in text, 'echo(text: str)' in text)")
    expect("both tools are described", r.stdout == "True True\n")

    title("tool_help With An Unknown Tool")
    r = run(sand, "tool_help(['inconnu'])")
    expect("NameError that lists the available tools",
           "NameError" in r.error and "add" in r.error)

    title("tool_help With A List That Contains A Non-String")
    r = run(sand, "tool_help(['add', 3])")
    expect("TypeError", "TypeError" in r.error)

    title("tool_help With Something That Is Not A List")
    r = run(sand, "tool_help(42)")
    expect("TypeError", "TypeError" in r.error)


def test_no_mcp(config: SandboxConfig) -> None:
    title("Sandbox Without MCP")
    with Sandbox(None, config) as sand:
        r = run(sand, "print(1)")
        expect("works without any MCP server", r.stdout == "1\n")
        r = run(sand, "add(1, 1)")
        expect("tools do not exist (NameError)", "NameError" in r.error)
        r = run(sand, "tool_help(['add'])")
        expect("tool_help does not exist (NameError)",
               "NameError" in r.error)
        manual = sand.get_manual()
        print(manual)
        expect("no Tools section in the manual", "## Tools" not in manual)
        expect("no placeholder left", "$" not in manual)
        expect("final_answer is still documented", "final_answer" in manual)


# --------------------------------------------------------------------------
# Echo of the REPL
# --------------------------------------------------------------------------

def test_echo(config: SandboxConfig) -> None:
    title("Echo Of Expression Values (REPL mode)")
    with Sandbox(MCP_COMMAND, config, echo=True) as sand:
        r = run(sand, "1 + 1")
        expect("1 + 1 prints 2", r.stdout == "2\n")
        r = run(sand, "x = 5")
        expect("an assignment prints nothing", r.stdout == "")
        r = run(sand, "x")
        expect("a variable name prints its value", r.stdout == "5\n")
        r = run(sand, "print('a')")
        expect("print does not add a None", r.stdout == "a\n")
        r = run(sand, "x = 1\nprint(x)\nx + 1")
        expect("several statements in one block", r.stdout == "1\n2\n")
        r = run(sand, "def f():\n    return 1\nf()")
        expect("a function definition followed by a call",
               r.stdout == "1\n")
        r = run(sand, "add(1, 1)")
        expect("a tool result is echoed with quotes", r.stdout == "'2'\n")
        r = run(sand, "1 / 0")
        expect("errors are still reported", "ZeroDivisionError" in r.error)
        r = run(sand, "final_answer('b')")
        expect("final_answer still works", r.final_answer == "b")


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
    with Sandbox(MCP_COMMAND, crash_config) as sand:
        title("Crash Test")
        run(sand, "x = 1")
        r = run(sand, "import os\nos.kill(os.getpid(), 9)")
        expect("crash message returned, no exception raised",
               "crashed" in r.error)
        r = run(sand, "print(x)")
        expect("variables are lost after the restart (NameError)",
               "NameError" in r.error)
        r = run(sand, "print(add(1, 1))")
        expect("MCP tools still work in the new worker", r.stdout == "2\n")


def test_network(config: SandboxConfig) -> None:
    # socket is allowed here so that only the network block protects us.
    net_config = config.model_copy(update={
        "authorized_imports": config.authorized_imports + ["socket"],
    })
    with Sandbox(MCP_COMMAND, net_config) as sand:
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


# --------------------------------------------------------------------------
# Life cycle
# --------------------------------------------------------------------------

def test_context_manager(config: SandboxConfig) -> None:
    title("Context Manager")
    with Sandbox(MCP_COMMAND, config) as sand:
        r = run(sand, "print(1)")
    expect("works inside the with block", r.stdout == "1\n")
    time.sleep(0.5)
    expect("no worker alive after the with block",
           len(mp.active_children()) == 0)

    title("Exception Inside The With Block")
    raised = False
    try:
        with Sandbox(MCP_COMMAND, config):
            raise ValueError("test")
    except ValueError:
        raised = True
    expect("the exception is not swallowed", raised)
    time.sleep(0.5)
    expect("no worker alive afterwards", len(mp.active_children()) == 0)


def test_interrupt(config: SandboxConfig) -> None:
    title("Ctrl+C During execute (simulated)")
    long_config = config.model_copy(update={"max_execution_time_seconds": 10})
    sand = Sandbox(MCP_COMMAND, long_config)
    timer = threading.Timer(1.0, lambda: os.kill(os.getpid(), signal.SIGINT))
    interrupted = False
    start = time.monotonic()
    timer.start()
    try:
        sand.execute("while True:\n    pass")
    except KeyboardInterrupt:
        interrupted = True
    finally:
        timer.cancel()
        sand.close()
    elapsed = time.monotonic() - start
    expect("KeyboardInterrupt reaches the caller", interrupted)
    expect(f"the sandbox stops quickly ({elapsed:.1f} s < 5 s)", elapsed < 5)
    time.sleep(0.5)
    expect("no worker left behind", len(mp.active_children()) == 0)
    left = server_processes_left()
    if left is None:
        print("pgrep is not available: server check skipped")
    else:
        expect("no MCP server process left", not left)


def test_lifecycle(config: SandboxConfig) -> None:
    title("Default Configuration")
    with Sandbox(MCP_COMMAND) as sand:
        r = run(sand, "print(add(1, 1))")
        expect("works with the default SandboxConfig", r.stdout == "2\n")

    title("MCP Command Is Required")
    try:
        leaked = Sandbox()  # type: ignore[call-arg]
    except TypeError as e:
        print(f"Raised TypeError: {e}")
        required = True
    else:
        leaked.close()           # do not leave a worker behind
        required = False
    expect("Sandbox() without a command raises TypeError "
           "(remove this check if mcp_command has a default value)",
           required)

    title("Unknown MCP Program")
    expect_connection_error("doesnotexist", config, 5, "doesnotexist")

    title("MCP Script Not Found")
    expect_connection_error("python test/this_script_does_not_exist.py",
                            config, 5, "this_script_does_not_exist")

    title("URL With An Unsupported Scheme")
    expect_connection_error("ftp://127.0.0.1/mcp", config, 5, "scheme")

    title("URL Without A Host")
    expect_connection_error("http://", config, 5, "host")

    if not QUICK:
        title("MCP Process That Never Answers (takes about 15 s)")
        expect_connection_error('python -c "import time; time.sleep(60)"',
                                config, 30)

        title("HTTP URL Where Nothing Listens (takes up to 15 s)")
        expect_connection_error(f"http://127.0.0.1:{free_port()}/mcp",
                                config, 20)

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


# --------------------------------------------------------------------------
# HTTP transport
# --------------------------------------------------------------------------

def test_http(config: SandboxConfig) -> None:
    server = start_http_server()
    if server is None:
        return
    try:
        with Sandbox(HTTP_URL, config) as sand:
            title("HTTP Transport: Tool Call")
            r = run(sand, "print(add(1, 1))")
            expect("add(1, 1) gives 2", r.stdout == "2\n")

            title("HTTP Transport: Tool Error")
            r = run(sand, "fail()")
            expect("the server message reaches the error field",
                   "always fails" in r.error)

            title("HTTP Transport: Manual")
            manual = sand.get_manual()
            expect("the tools are listed", "add(" in manual)

        title("The HTTP Server Survives The Sandbox")
        expect("the server is still running after close()",
               server.poll() is None)

        title("HTTP URL Without The Path")
        expect_connection_error(f"http://127.0.0.1:{HTTP_PORT}/", config, 30)
    finally:
        stop_server(server)


def test_http_server_dies(config: SandboxConfig) -> None:
    server = start_http_server()
    if server is None:
        return
    sand = Sandbox(HTTP_URL, config)
    try:
        title("HTTP Server Dies During The Session (may take up to 30 s)")
        r = run(sand, "print(add(1, 1))")
        expect("works while the server is up", r.stdout == "2\n")
        stop_server(server)
        r = run(sand, "print(add(1, 1))")
        expect("the failure is reported as an error, no crash",
               r.error != "")
        r = run(sand, "print('alive')")
        expect("the sandbox is still usable", r.stdout == "alive\n")
    finally:
        sand.close()
        stop_server(server)


# --------------------------------------------------------------------------
# REPL and CLI
# --------------------------------------------------------------------------

def test_repl_helpers() -> None:
    title("REPL: Detection Of Complete Statements")
    cases = [
        ("1 + 1", True, "an expression is complete"),
        ("x = 1", True, "an assignment is complete"),
        ("def f():", False, "a line ending with ':' is incomplete"),
        ("x = (1,", False, "an open parenthesis is incomplete"),
        ("'''abc", False, "an open triple quote is incomplete"),
        ("if True:\n    pass", False,
         "a block is not complete until an empty line"),
        ("if True:\n    pass\n", True,
         "a block followed by an empty line is complete"),
        ("1 +", True, "a syntax error is sent anyway"),
    ]
    for source, expected, label in cases:
        expect(label, is_complete(source) is expected)


def run_cli(cli: str, args: List[str],
            stdin: str) -> subprocess.CompletedProcess:
    process = subprocess.run([cli, *args], input=stdin, capture_output=True,
                             text=True, timeout=120)
    print(f"Return code: {process.returncode}")
    print(f"STDOUT: {process.stdout[-300:]!r}")
    print(f"STDERR: {process.stderr[-300:]!r}")
    return process


def test_cli() -> None:
    cli = shutil.which("sandbox")
    if cli is None:
        print("The 'sandbox' command is not installed: CLI sections "
              "skipped (run this script through `uv run`)")
        return

    title("CLI: --help")
    p = run_cli(cli, ["--help"], "")
    expect("exit code 0 and both MCP options are described",
           p.returncode == 0 and "--mcp-stdio" in p.stdout
           and "--mcp-server" in p.stdout)

    title("CLI: REPL Without MCP")
    p = run_cli(cli, [], "1 + 1\nexit\n")
    expect("2 is printed and the exit code is 0",
           p.returncode == 0 and "2" in p.stdout)

    title("CLI: REPL With A Configuration File")
    p = run_cli(cli, [CONFIG_PATH], "1 + 1\nexit\n")
    expect("2 is printed and the exit code is 0",
           p.returncode == 0 and "2" in p.stdout)

    title("CLI: REPL With --mcp-stdio")
    p = run_cli(cli, ["--mcp-stdio", MCP_COMMAND], "add(1, 1)\nexit\n")
    expect("the tool result is printed and the exit code is 0",
           p.returncode == 0 and "2" in p.stdout)

    title("CLI: End Of Input (Ctrl+D)")
    p = run_cli(cli, [], "")
    expect("exits cleanly with code 0", p.returncode == 0)

    title("CLI: Configuration File That Does Not Exist")
    p = run_cli(cli, ["this_config_does_not_exist.json"], "")
    expect("exit code 1 and no traceback",
           p.returncode == 1 and "Traceback" not in p.stderr)

    title("CLI: Invalid JSON Configuration")
    bad = Path(tempfile.mkdtemp()) / "bad.json"
    bad.write_text("{not json")
    p = run_cli(cli, [str(bad)], "")
    expect("exit code 1 and no traceback",
           p.returncode == 1 and "Traceback" not in p.stderr)

    title("CLI: Unknown MCP Program")
    p = run_cli(cli, ["--mcp-stdio", "doesnotexist"], "")
    expect("exit code 1, a clear message and no traceback",
           p.returncode == 1 and "Traceback" not in p.stderr
           and "Cannot start the sandbox" in p.stderr)

    title("CLI: --mcp-stdio And --mcp-server Together")
    p = run_cli(cli, ["--mcp-stdio", "x", "--mcp-server", HTTP_URL], "")
    expect("refused by argparse (exit code 2)", p.returncode == 2)

    if not QUICK:
        title("CLI: HTTP Server That Is Not Running (takes up to 15 s)")
        p = run_cli(cli, ["--mcp-server",
                          f"http://127.0.0.1:{free_port()}/mcp"], "")
        expect("exit code 1 and no traceback",
               p.returncode == 1 and "Traceback" not in p.stderr)


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
    global BASELINE_SERVER_PIDS
    BASELINE_SERVER_PIDS = server_pids() or set()
    base = load_config(CONFIG_PATH)
    config = base.model_copy(update={
        "max_execution_time_seconds": 3,   # keep timeout tests fast
        "max_len_output": 200,             # small limit to test truncation
        "max_len_tool_output": 500,        # same, for tool results
    })
    os.makedirs("/tmp/agent", exist_ok=True)

    sand = Sandbox(MCP_COMMAND, config)
    try:
        attempt(test_basics, sand)
        attempt(test_final_answer, sand)
        attempt(test_errors, sand)
        attempt(test_imports, sand)
        attempt(test_builtins, sand)
        attempt(test_files, sand)
        attempt(test_truncation, sand)
        attempt(test_mcp_tools, sand)
        attempt(test_mcp_errors, sand)
        attempt(test_manual, sand)
        attempt(test_tool_help, sand)
        attempt(test_mcp_limits, sand)
        attempt(test_memory, sand)
        attempt(test_timeouts, sand)
    finally:
        sand.close()

    attempt(test_crash, config)
    attempt(test_network, config)
    attempt(test_no_mcp, config)
    attempt(test_manual_follows_config, config)
    attempt(test_echo, config)
    attempt(test_context_manager, config)
    attempt(test_interrupt, config)
    attempt(test_lifecycle, config)
    if not QUICK:
        attempt(test_http_server_dies, config)
    attempt(test_http, config)
    attempt(test_repl_helpers)
    attempt(test_cli)
    attempt(test_no_leftovers)
    return summary()


if __name__ == "__main__":
    sys.exit(main())