from .McpClient import McpClient, ToolSpec
from typing import Dict, Any
import asyncio
import threading
import concurrent.futures

TIMEOUT_CALL_TOOL = 30
TIMEOUT_CLIENT_CONN = 15
TIMEOUT_CLOSE = 5


class McpBridge:
    def __init__(self, command: str) -> None:
        self._client = McpClient(command)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True
        )
        self._thread.start()
        self._closed = False
        self._ready: concurrent.futures.Future = concurrent.futures.Future()
        self._stop = asyncio.Event()
        self._owner_future = None

    def connect(self) -> None:
        try:
            self._owner_future = asyncio.run_coroutine_threadsafe(
                self._owner(),
                self._loop
            )
            self._ready.result(timeout=TIMEOUT_CLIENT_CONN)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        self._loop.call_soon_threadsafe(self._stop.set)
        if self._owner_future is not None:
            try:
                self._owner_future.result(timeout=TIMEOUT_CLOSE)
            except Exception:
                pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=TIMEOUT_CLOSE)
        if not self._loop.is_running():
            self._loop.close()

    async def _owner(self) -> None:
        try:
            await self._client.connect()
        except Exception as e:
            self._ready.set_exception(e)
            return
        self._ready.set_result(None)
        await self._stop.wait()
        await self._client.close()

    def _run(self, coro, timeout: float) -> Any:
        if self._closed:
            raise RuntimeError("The MCP bridge is closed")
        future = asyncio.run_coroutine_threadsafe(
            coro,
            self._loop
        )
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise

    def call_tool(self, func_name: str, args: Dict) -> str | Any:
        return self._run(
            self._client.call_tool(func_name, args),
            TIMEOUT_CALL_TOOL
        )

    def get_tools_list(self) -> Dict[str, ToolSpec] | Any:
        return self._run(
            self._client.get_mcp_tool(),
            TIMEOUT_CALL_TOOL
        )
