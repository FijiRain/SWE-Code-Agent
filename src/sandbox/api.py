from .ExecutionResult import ExecutionResult, FinalAnswerSignal
from .SandboxConfig import SandboxConfig

from typing import Dict
from contextlib import redirect_stdout
import multiprocessing as mp
from multiprocessing.connection import Connection
import io


def code_worker_loop(conn: Connection) -> None:
    namespace: Dict = {}

    def final_answer(value):
        raise FinalAnswerSignal(value)
    namespace["final_answer"] = final_answer

    while True:
        code = conn.recv()
        if code is None:
            break

        buffer = io.StringIO()
        exec_res = ExecutionResult()
        try:
            with redirect_stdout(buffer):
                exec(code, namespace)
        except FinalAnswerSignal as signal:
            exec_res.final_answer = signal.value
        except Exception as e:
            exec_res.error = f"Error {type(e).__name__}: {e}"
        finally:
            exec_res.stdout = buffer.getvalue()

        conn.send(exec_res)


class Sandbox:
    """Execute LLM generated code in a restricted environement"""
    def __init__(self,
                 sandbox_config: SandboxConfig | None = None) -> None:
        """Init sandbox"""
        self.__config = sandbox_config or SandboxConfig()

        ctx = mp.get_context("spawn")
        self._conn, child_con = ctx.Pipe()
        self._process = ctx.Process(target=code_worker_loop, args=(child_con,))
        self._process.start()
        child_con.close()

    def execute(self, code: str) -> ExecutionResult:
        """Execute the code"""
        self._conn.send(code)
        return self._conn.recv()

    def get_manual(self) -> str:
        """Return the sandbox manual"""
        ...

    def close(self) -> None:
        """Kill the running process"""
        self._conn.send(None)
        self._process.join()
