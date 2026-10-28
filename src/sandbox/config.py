"""Constants of the sandbox: timeouts and terminal colors."""
from pathlib import Path
from typing import Dict, Any
import sys

# Worker
START_WORK_TIMEOUT = 10

# Bridge
TIMEOUT_CALL_TOOL = 30
TIMEOUT_CLIENT_CONN = 15
TIMEOUT_CLOSE = 5

# Color
USE_COLOR = sys.stdout.isatty()
RED = "\033[1;31m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""

# Manual
TEMPLATE_MANUAL_PATH = (
    Path(__file__).parent / "templates" / "manual_all_tool.txt"
)
JSON_TO_PY: Dict[Any, str] = {
    "string": "str", "integer": "int", "number": "float",
    "boolean": "bool", "object": "dict", "null": "None"
}

MCP_COMMAND = "python mcp_tools_mbpp.py"
