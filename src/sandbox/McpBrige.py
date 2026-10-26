"""Synchronous bridge to the asynchronous MCP client."""
from .McpClient import McpClient, ToolSpec
from typing import Dict, Any, Coroutine
import asyncio
import threading
import concurrent.futures

TIMEOUT_CALL_TOOL = 30
TIMEOUT_CLIENT_CONN = 15
TIMEOUT_CLOSE = 5


class McpBridge:
    """Run an McpClient in a background event loop and expose sync calls.

    A dedicated thread runs the event loop. The ``_owner`` coroutine opens
    the connection and keeps it alive until close() is called, so that the
    session is opened and closed in the same task.
    """

    def __init__(self, command: str) -> None:
        """Create the client and start the event loop thread.

        Args:
            command: Command line that starts the MCP server.
        """
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
        self._owner_future: concurrent.futures.Future | None = None

    def connect(self) -> None:
        """Connect to the server and wait until the session is ready.

        The bridge is closed if the connection fails or times out.

        Raises:
            McpConnectionError: If the server cannot be reached.
            concurrent.futures.TimeoutError: If the connection takes more
                than TIMEOUT_CLIENT_CONN seconds.
        """
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
        """Close the MCP session and stop the event loop thread.

        Calling it more than once does nothing.
        """
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
        """Open the connection, wait for the stop event, then close it."""
        try:
            await self._client.connect()
        except Exception as e:
            self._ready.set_exception(e)
            return
        self._ready.set_result(None)
        await self._stop.wait()
        await self._client.close()

    def _run(self, coro: Coroutine[Any, Any, Any], timeout: float) -> Any:
        """Run a coroutine in the event loop and wait for its result.

        Args:
            coro: Coroutine to run.
            timeout: Maximum time to wait, in seconds.

        Raises:
            RuntimeError: If the bridge is closed.
            concurrent.futures.TimeoutError: If the coroutine takes too
                long; it is cancelled.
        """
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
        """Call an MCP tool and return its text result."""
        return self._run(
            self._client.call_tool(func_name, args),
            TIMEOUT_CALL_TOOL
        )

    def get_tools_list(self) -> Dict[str, ToolSpec] | Any:
        """Return the tools exposed by the server, indexed by name."""
        return self._run(
            self._client.get_mcp_tool(),
            TIMEOUT_CALL_TOOL
        )
