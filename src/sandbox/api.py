from .ExecutionResult import ExecutionResult, FinalAnswerSignal
from .SandboxConfig import SandboxConfig

from typing import Dict
from contextlib import redirect_stdout
import multiprocessing as mp
from multiprocessing.connection import Connection
import io

STARTUP_TIMEOUT = 10


def code_worker_loop(conn: Connection) -> None:
    namespace: Dict = {}

    def final_answer(value):
        raise FinalAnswerSignal(value)
    namespace["final_answer"] = final_answer

    conn.send("ready")
    while True:
        code = conn.recv()
        if code is None:
            break

        buffer = io.StringIO()
        exec_res = ExecutionResult()
        try:
            with redirect_stdout(buffer):
                exec(code, namespace)
        except SystemExit:
            exec_res.error = ("SystemExit: exit()/sys.exit() are not allowed "
                              "in the sandbox. "
                              "Call final_answer(...) to finish the task.")
        except FinalAnswerSignal as signal:
            exec_res.final_answer = str(signal.value)
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

        self._start_work_process()

    def _start_work_process(self) -> None:
        """Init the launche of work process to execut code"""
        ctx = mp.get_context("spawn")
        self._conn, child_con = ctx.Pipe()
        self._process = ctx.Process(target=code_worker_loop, args=(child_con,))
        self._process.start()
        child_con.close()
        if not self._conn.poll(STARTUP_TIMEOUT):
            self._process.kill()
            raise RuntimeError("The worker process failed to start")
        self._conn.recv()

    def _restart_work_process(self) -> None:
        self.close()
        self._start_work_process()

    def execute(self, code: str) -> ExecutionResult:
        """Execute the code"""
        timed_out = False
        try:
            self._conn.send(code)
            if self._conn.poll(self.__config.max_execution_time_seconds):
                return self._conn.recv()
            timed_out = True
        except (EOFError, OSError):
            pass
        self._restart_work_process()
        if timed_out:
            return ExecutionResult(
                error=(
                        f"TimeoutError: your code did not finish within "
                        f"{self.__config.max_execution_time_seconds} "
                        "seconds and was stopped "
                        "(possible infinite loop or too heavy computation). "
                        "The execution environment was restarted: all "
                        "variables and imports "
                        "are lost, you must redefine them. "
                        "Output printed before the timeout is not available."
                    ),
                timed_out=True
                    )
        return ExecutionResult(
                error=(
                        "The execution environment crashed "
                        "(e.g. os._exit). "
                        "A new empty environment was "
                        "started: all variables are lost."
                ))

    def get_manual(self) -> str:
        """Return the sandbox manual"""
        ...

    def close(self) -> None:
        """Kill the running process"""
        try:
            self._conn.send(None)
        except (EOFError, OSError):
            pass
        self._process.join(timeout=1)
        if self._process.is_alive():
            self._process.kill()
            self._process.join()
        self._conn.close()
