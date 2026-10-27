from .api import Sandbox
from .SandboxConfig import SandboxConfig
from .ExecutionResult import ExecutionResult

from typing import List
import codeop
import sys
import readline


USE_COLOR = sys.stdout.isatty()
RED = "\033[1;31m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


def is_complet(source: str) -> bool:
    try:
        return codeop.compile_command(source, "<repl>", "single") is not None
    except (SyntaxError, ValueError, OverflowError):
        return True


def display(result: ExecutionResult) -> None:
    """Print an ExecutionResult the way a Python REPL would."""
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.error:
        print(f"{RED}{result.error}{RESET}")
    notes = [text for flag, text in ((result.timed_out, "timed out"),
                                     (result.truncated, "output truncated"))
             if flag]
    if notes:
        print(f"[{', '.join(notes)}]")
    if result.final_answer is not None:
        print(f"final_answer: {result.final_answer}")


def repl(
        mcp_command: str,
        sandbox_config: SandboxConfig | None = None,
        ) -> None:
    buffer: List[str] = []
    sand = Sandbox(mcp_command, sandbox_config, True)
    while True:
        try:
            line = input("... " if buffer else ">>> ")
            if not line.strip():
                line = ""
        except EOFError:
            break
        except KeyboardInterrupt:
            buffer.clear()
            continue
        if not buffer and line.strip() in ("exit", "exit()"):
            break
        buffer.append(line)
        source = "\n".join(buffer)
        if not source.strip() or not is_complet(source):
            if not source.strip():
                buffer.clear()
            continue
        buffer.clear()
        result = sand.execute(source)
        display(result)
    sand.close()
