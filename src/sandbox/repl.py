"""Interactive read-eval-print loop running code in the sandbox."""
from .api import Sandbox
from ..models.ExecutionResult import ExecutionResult
from .config import RESET, RED, CONTINUATION

from typing import List
import codeop
import readline  # noqa: F401
import sys


def is_complet(source: str) -> bool:
    """Return True if the source can be executed without more lines.

    Invalid source counts as complete, so that its error is shown.
    """
    try:
        return codeop.compile_command(source, "<repl>", "single") is not None
    except (SyntaxError, ValueError, OverflowError):
        return True


def block_state(source: str) -> str:
    """Return "incomplete", "complete" or "error" for a block of code.

    Unlike is_complet, the whole buffer is compiled in "exec" mode, so an
    open string, bracket or block header is reported as incomplete.
    """
    try:
        code = codeop.compile_command(source, "<repl>", "exec")
    except (SyntaxError, ValueError, OverflowError):
        return "error"
    return "incomplete" if code is None else "complete"


def is_continuation(line: str) -> bool:
    """Return True if the line continues the previous block (else, ...)."""
    stripped = line.lstrip()
    return any(stripped.startswith(word)
               and stripped[len(word):len(word) + 1] in (":", " ")
               for word in CONTINUATION)


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
    interactive = sys.stdin.isatty()

    def flush() -> bool:
        """Run the buffered block. Return False if the REPL must stop."""
        source = "\n".join(buffer)
        buffer.clear()
        if not source.strip():
            return True
        try:
            display(sandbox.execute(source))
        except KeyboardInterrupt:
            print("\nInterrupted, sandbox closed.")
            return False
        return True

    while True:
        try:
            line = input("... " if buffer else ">>> ")
        except EOFError:
            flush()
            print("KeyboardInterrupt")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            buffer.clear()
            continue

        if not buffer:
            if not line.strip():
                continue
            if line.strip() in ("exit", "exit()"):
                break
            buffer.append(line)
        elif (interactive and not line.strip()
              and block_state("\n".join(buffer)) != "incomplete"):
            if not flush():
                return
            continue
        elif not line.strip() or line[0] in " \t":
            buffer.append(line)
            continue
        elif (is_continuation(line)
              or block_state("\n".join(buffer)) == "incomplete"):
            buffer.append(line)
            continue
        else:
            if not flush():
                return
            if line.strip() in ("exit", "exit()"):
                break
            buffer.append(line)
        if len(buffer) == 1 and block_state(line) == "complete" \
                and not line.rstrip().endswith(":"):
            if not flush():
                return
    sandbox.close()
