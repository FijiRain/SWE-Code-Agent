"""Public sandbox API: run LLM generated code in a worker process."""
from ..models.ExecutionResult import ExecutionResult
from ..models.SandboxConfig import SandboxConfig
from .restricted_sandbox import truncke_output
from .McpBrige import McpBridge
from ..models.ToolSpec import ToolSpec
from .wrapper_tools import WorkerToolMessageIntput
from .manual_manager import build_manual
from .worker import code_worker_loop
from .config import START_WORK_TIMEOUT

from typing import Any, Dict, List, cast
import multiprocessing as mp
import time
import concurrent.futures


class Sandbox:
    """Execute LLM generated code in a restricted environment.

    The code runs in a separate worker process. Variables persist between
    calls to execute() until the worker is restarted (timeout or crash).
    MCP tool calls made by the code are forwarded by the main process to
    the MCP server.
    """

    def __init__(self,
                 mcp_command: str | None = None,
                 sandbox_config: SandboxConfig | None = None,
                 echo: bool = False
                 ) -> None:
        """Connect to the MCP server and start the worker process.

        Args:
            mcp_command: Command line that starts the MCP server.
            sandbox_config: Sandbox configuration, the default one if None.

        Raises:
            McpConnectionError: If the MCP server cannot be reached.
            RuntimeError: If the worker process fails to start.
        """
        self._echo = echo
        self.__config = sandbox_config or SandboxConfig()
        self._tools_list: Dict[str, ToolSpec] = {}
        self._mcp_bridge: McpBridge | None = None

        if mcp_command is not None:
            self._mcp_bridge = McpBridge(mcp_command)
            try:
                self._mcp_bridge.connect()
                self._tools_list = self._mcp_bridge.get_tools_list()
            except BaseException:
                self._mcp_bridge.close()
                raise
        try:
            self._start_work_process()
        except BaseException:
            if self._mcp_bridge is not None:
                self._mcp_bridge.close()
            raise

    def _start_work_process(self) -> None:
        """Start the worker process and wait for its "ready" message.

        Raises:
            RuntimeError: If the worker does not answer within
                STARTUP_TIMEOUT seconds or dies during startup.
        """
        ctx = mp.get_context("spawn")
        self._conn, child_con = ctx.Pipe()
        self._process = ctx.Process(
            target=code_worker_loop,
            args=(
                child_con,
                self.__config,
                self._tools_list,
                self._echo
            ),
            daemon=True
        )
        self._process.start()
        child_con.close()
        if not self._conn.poll(START_WORK_TIMEOUT):
            self._process.kill()
            self._conn.close()
            raise RuntimeError("The worker process failed to start")
        try:
            self._conn.recv()
        except EOFError:
            self._process.join()
            self._conn.close()
            raise RuntimeError(
                "The worker process died during startup "
                f"(exit code {self._process.exitcode}), see "
                "its traceback above"
            )

    def _restart_work_process(self) -> None:
        """Replace the worker by a new one with an empty namespace."""
        self._stop_worker()
        self._start_work_process()

    def execute(self, code: str) -> ExecutionResult:
        """Execute code in the worker and return its result.

        Stdout is collected while the code runs, and tool calls are
        forwarded to the MCP server. Time spent in tools is not counted in
        the timeout. On timeout or crash the worker is restarted and all
        variables are lost.

        Args:
            code: Python source code to execute.

        Returns:
            The execution result, with stdout truncated to max_len_output.
        """
        timed_out = False
        chunks: List[str] = []
        deadline = time.monotonic() + self.__config.max_execution_time_seconds
        tool_truncated = False
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
                elif state == "tool_call":
                    start_time_tool = time.monotonic()
                    message_intput = WorkerToolMessageIntput()
                    try:
                        if self._mcp_bridge is None:
                            raise RuntimeError(
                                "No MCP server connected"
                            )
                        message_intput.output = self._mcp_bridge.call_tool(
                            payload.name,
                            payload.args
                        )
                        message_intput.output, cut = truncke_output(
                            message_intput.output,
                            self.__config.max_len_tool_output
                        )
                        tool_truncated = tool_truncated or cut
                    except (Exception, concurrent.futures.TimeoutError) as e:
                        message_intput.error = True
                        message_intput.output = (
                            f"{type(e).__name__}: {e}"
                        )
                    self._conn.send(("tool_result", message_intput))
                    deadline += time.monotonic() - start_time_tool

                else:
                    output = "".join(chunks)
                    output, is_truncate = truncke_output(
                        output, self.__config.max_len_output
                    )
                    payload.stdout = output
                    payload.truncated = is_truncate or tool_truncated
                    return cast(ExecutionResult, payload)

        except (EOFError, OSError):
            pass
        except KeyboardInterrupt:
            self.close()
            raise
        self._restart_work_process()
        output = "".join(chunks)
        output, is_truncate = truncke_output(
            output, self.__config.max_len_output
        )
        if timed_out:
            return ExecutionResult(
                stdout=output,
                error=(
                        f"TimeoutError: your code did not finish within "
                        f"{self.__config.max_execution_time_seconds} "
                        "seconds and was stopped "
                        "(possible infinite loop or too heavy computation). "
                        "The execution environment was restarted: all "
                        "variables and imports "
                        "are lost, you must redefine them. "
                    ),
                timed_out=True,
                truncated=is_truncate or tool_truncated
                    )
        return ExecutionResult(
                stdout=output,
                error=(
                        "The execution environment crashed "
                        "(e.g. os._exit). "
                        "A new empty environment was "
                        "started: all variables are lost."
                ),
                truncated=is_truncate
            )

    def get_manual(self) -> str:
        """Return the sandbox manual"""
        return build_manual(self.__config, self._tools_list)

    def _stop_worker(self) -> None:
        """Ask the worker to stop, kill it if needed and close the pipe."""
        try:
            self._conn.send(None)
        except (EOFError, OSError):
            pass
        self._process.join(timeout=1)
        if self._process.is_alive():
            self._process.kill()
            self._process.join()
        self._conn.close()

    def close(self) -> None:
        """Stop the worker process and close the MCP connection."""
        self._stop_worker()
        if self._mcp_bridge is not None:
            self._mcp_bridge.close()

    def __enter__(self) -> "Sandbox":
        """Return the sandbox itself for use in a with statement."""
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Close the sandbox when leaving the with statement."""
        self.close()
