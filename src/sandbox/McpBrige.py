from .McpClient import McpClient
import asyncio
import threading


class McpBridge:
    def __init__(self) -> None:
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop, daemon=True)
        thread .start()
