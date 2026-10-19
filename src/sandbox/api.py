from .ExecutionResult import ExecutionResult, FinalAnswerSignal
from .SandboxConfig import SandboxConfig
from .restricted_sandbox import build_builtins

from typing import Dict, List
from contextlib import redirect_stdout
import multiprocessing as mp
from multiprocessing.connection import Connection
import time


STARTUP_TIMEOUT = 10


class PipeWriter:
    """
    Class to write in Pip text on the main process
    This is an emulation to allow the use of os.stdout.write.
    """
    def __init__(self, conn: Connection) -> None:
        """Init object withe connection at Pipe"""
        self._conn = conn

    def write(self, text: str) -> int:
        """Send text in Pipe"""
        if text:
            self._conn.send(("stdout", text))
        return len(text)

    def flush(self) -> None:
        """ obligatory function"""
        pass


def code_worker_loop(conn: Connection, config: SandboxConfig) -> None:
    namespace: Dict = {
        "__builtins__": build_builtins(config),
        "__name__": config.name_space_global,
    }

    state_final_answer = {"answer": None}

    def final_answer(value):
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

        buffer = PipeWriter(conn)
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

        conn.send(("result", exec_res))


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
        self._process = ctx.Process(target=code_worker_loop,
                                    args=(child_con, self.__config))
        self._process.start()
        child_con.close()
        if not self._conn.poll(STARTUP_TIMEOUT):
            self._process.kill()
            self._conn.close()
            raise RuntimeError("The worker process failed to start")
        self._conn.recv()

    def _restart_work_process(self) -> None:
        self.close()
        self._start_work_process()

    def execute(self, code: str) -> ExecutionResult:
        """Execute the code"""
        timed_out = False
        chunks: List[str] = []
        deadline = time.monotonic() + self.__config.max_execution_time_seconds
        try:
            self._conn.send(code)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._conn.poll(remaining):
                    timed_out = True
                    break
                state, payload = self._conn.recv()
                if state == "stdout":
                    chunks.append(payload)
                else:
                    payload.stdout = "".join(chunks)
                    return payload

        except (EOFError, OSError):
            pass
        self._restart_work_process()
        if timed_out:
            return ExecutionResult(
                stdout="".join(chunks),
                error=(
                        f"TimeoutError: your code did not finish within "
                        f"{self.__config.max_execution_time_seconds} "
                        "seconds and was stopped "
                        "(possible infinite loop or too heavy computation). "
                        "The execution environment was restarted: all "
                        "variables and imports "
                        "are lost, you must redefine them. "
                    ),
                timed_out=True
                    )
        return ExecutionResult(
                stdout="".join(chunks),
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
