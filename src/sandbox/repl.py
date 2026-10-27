"""Interactive read-eval-print loop running code in the sandbox."""
from .api import Sandbox
from ..models.ExecutionResult import ExecutionResult
from .config import RESET, RED

from typing import List
import codeop
import readline  # noqa: F401


def is_complet(source: str) -> bool:
    """Return True if the source can be executed without more lines.

    Invalid source counts as complete, so that its error is shown.
    """
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


def repl(sandbox: Sandbox) -> None:
    """Read code from the terminal and execute it in the sandbox.

    Lines are buffered until the block is complete. The loop stops on
    "exit", "exit()" or EOF, and the sandbox is then closed.

    Args:
        sandbox: Sandbox in which the code is executed.
    """
    buffer: List[str] = []
    while True:
        try:
            line = input("... " if buffer else ">>> ")
            if not line.strip():
                line = ""
        except EOFError:
            print("KeyboardInterrupt")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
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
        try:
            display(sandbox.execute(source))
        except KeyboardInterrupt:
            print("\nInterrupted, sandbox closed.")
            return
    sandbox.close()
