from .api import Sandbox
from .SandboxConfig import SandboxConfig

from typing import List
import codeop
import readline


def is_complet(source: str) -> bool:
    try:
        return codeop.compile_command(source, "<repl>", "single") is not None
    except (SyntaxError, ValueError, OverflowError):
        return True


def repl(
        mcp_command: str,
        sandbox_config: SandboxConfig | None = None,
        ) -> None:
    buffer: List[str] = []
    sand = Sandbox(mcp_command, sandbox_config)
    while True:
        try:
            line = input("... " if buffer else ">>> ")
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
        if result.error:
            print(result.error)
        else:
            print(result.stdout)
    sand.close()
