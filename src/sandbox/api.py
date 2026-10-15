from .ExecutionResult import ExecutionResult, FinalAnswerSignal
from .SandboxConfig import SandboxConfig

from typing import Dict
from contextlib import redirect_stdout
import io


class Sandbox:
    """Execute LLM generated code in a restricted environement"""
    def __init__(self,
                 sandbox_config: SandboxConfig = SandboxConfig()) -> None:
        """Init sandbox"""
        self.__namespace: Dict = {}
        self.__config = sandbox_config

        def final_answer(value):
            raise FinalAnswerSignal(value)
        self.__namespace["final_answer"] = final_answer

    def execute(self, code: str) -> ExecutionResult:
        """Execute the code"""
        buffer = io.StringIO()
        exec_res = ExecutionResult()
        try:
            with redirect_stdout(buffer):
                exec(code, self.__namespace)
        except FinalAnswerSignal as signal:
            exec_res.final_answer = signal.value
        except Exception as e:
            exec_res.error = f"Error {type(e).__name__}: {e}"
        finally:
            exec_res.stdout = buffer.getvalue()

        return exec_res

    def get_manual(self) -> str:
        """Return the sandbox manual"""
        ...

    def close(self) -> None:
        """Relase the MCP connection and kill the running process"""
        ...