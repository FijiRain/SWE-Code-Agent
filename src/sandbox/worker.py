"""Worker process of the sandbox that executes the code snippets."""
from ..models.ExecutionResult import ExecutionResult, FinalAnswerSignal
from ..models.SandboxConfig import SandboxConfig
from ..models.ToolSpec import ToolSpec
from .restricted_sandbox import (
    build_builtins, apply_memory_restricted,
    restricted_conn
)
from .wrapper_tools import make_tools_wrapper
from .manual_manager import make_tool_help


from typing import Dict, NoReturn, Any
from multiprocessing.connection import Connection
from contextlib import redirect_stdout
import signal
import keyword
import ast


class PipeWriter:
    """File-like object that sends written text to the main process.

    Used with redirect_stdout so that print() and sys.stdout.write() in
    the worker are streamed through the pipe as ("stdout", text) messages.
    """

    def __init__(self, conn: Connection) -> None:
        """Store the pipe connection to the main process."""
        self._conn = conn

    def write(self, text: str) -> int:
        """Send text through the pipe and return its length."""
        if text:
            self._conn.send(("stdout", text))
        return len(text)

    def flush(self) -> None:
        """Do nothing, required by the file-like interface."""
        pass


def run_code(code: str, namespace: Dict, echo: bool) -> None:
    """Execute code in the namespace.

    With echo, each statement is run in "single" mode so that the value
    of an expression is printed, like in a Python REPL.

    Args:
        code: Python source code to execute.
        namespace: Globals of the execution.
        echo: True to print the value of expression statements.
    """
    if not echo:
        exec(code, namespace)
        return
    for node in ast.parse(code, "<string>", "exec").body:
        exec(
            compile(
                ast.Interactive(body=[node]), "<string>", "single"),
            namespace
        )


def code_worker_loop(
        conn: Connection,
        config: SandboxConfig,
        tools: Dict[str, ToolSpec],
        echo: bool
        ) -> None:
    """Run the worker process loop that executes code snippets.

    Apply the memory and network restrictions, build the restricted
    namespace (builtins, MCP tool wrappers, final_answer), then send
    "ready" and execute each received snippet until None or EOF. Every
    execution ends with a ("result", ExecutionResult) message.

    Args:
        conn: Pipe connection to the main process.
        config: Sandbox configuration.
        tools: MCP tools to expose in the namespace, indexed by name.
        echo: True to print the value of expression statements.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    apply_memory_restricted(config.max_memory_mb)
    restricted_conn()
    namespace: Dict = {
        "__builtins__": build_builtins(config),
        "__name__": config.sandbox_name,
    }

    for spec in tools.values():
        if not spec.name.isidentifier() or keyword.iskeyword(spec.name):
            continue
        namespace[spec.name] = make_tools_wrapper(spec, conn)

    if tools:
        namespace["tool_help"] = make_tool_help(tools)

    state_final_answer: Dict = {}
    state_final_answer["answer"] = None

    def final_answer(value: Any) -> NoReturn:
        """Record the final answer and stop the running code."""
        state_final_answer["answer"] = str(value)
        raise FinalAnswerSignal(value)
    namespace["final_answer"] = final_answer

    conn.send("ready")
    while True:
        try:
            code = conn.recv()
        except EOFError:
            break
        if code is None:
            break

        state_final_answer["answer"] = None
        buffer = PipeWriter(conn)
        exec_res = ExecutionResult()
        try:
            with redirect_stdout(buffer):
                run_code(code, namespace, echo)
                # exec(code, namespace)
        except SystemExit:
            exec_res.error = ("SystemExit: exit()/sys.exit() are not allowed "
                              "in the sandbox. "
                              "Call final_answer(...) to finish the task.")
        except KeyboardInterrupt:
            exec_res.error = (
                "KeyboardInterrupt: raising it is not allowed in the "
                "sandbox. Call final_answer(...) to finish the task."
            )
        except FinalAnswerSignal:
            pass
        except MemoryError:
            exec_res.error = (
                f"MemoryError: your code exceeded the memory limit "
                f"({config.max_memory_mb} MB). Use less memory "
                "(smaller data, generators, no huge lists)."
            )
        except Exception as e:
            exec_res.error = f"Error {type(e).__name__}: {e}"

        exec_res.final_answer = state_final_answer['answer']
        conn.send(("result", exec_res))
