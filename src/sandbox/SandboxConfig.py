"""Configuration of the sandbox and its JSON loader."""
from pydantic import BaseModel, Field, ValidationError
from typing import List
from pathlib import Path


class SandboxConfig(BaseModel):
    """Configuration of the sandbox.

    Uses an allowlist approach: only the imports, builtins and directories
    listed here are available, everything else is blocked. It also sets
    the time, memory and output size limits.
    """
    authorized_imports: List[str] = Field(
        default_factory=lambda: [
            "math", "math.*",
            "collections", "collections.*",
            "itertools", "re", "json",
            "typing", "typing.*",
            "functools", "operator",
            "heapq", "bisect", "copy",
            "string", "random",
            "datetime", "datetime.*",
            "array", "cmath",
        ]
    )
    allowed_directories: List[str] = Field(
        default_factory=lambda: [
            "/testbed", "/tmp/agent",
        ]
    )
    authorized_builtins: List[str] = Field(
        default_factory=lambda: [
            "abs", "aiter", "all", "anext", "any", "ascii",
            "bin", "bool", "bytearray", "bytes",
            "callable", "chr", "classmethod", "complex",
            "dict", "dir", "divmod", "enumerate",
            "filter", "float", "format", "frozenset",
            "hasattr", "hash", "hex",
            "id", "int", "isinstance", "issubclass", "iter",
            "len", "list", "map", "max", "memoryview",
            "min", "next", "object", "oct", "ord", "pow",
            "print", "property", "range", "repr", "reversed", "round",
            "set", "slice", "sorted", "staticmethod", "str",
            "sum", "super", "tuple", "type", "zip",
            "__build_class__",
            "False", "True", "None", "Ellipsis", "NotImplemented",
            "__debug__",
            "Exception", "ArithmeticError", "AssertionError",
            "AttributeError", "BufferError", "BytesWarning",
            "DeprecationWarning", "EOFError", "FloatingPointError",
            "FutureWarning", "GeneratorExit", "ImportError",
            "ModuleNotFoundError", "LookupError", "IndexError", "KeyError",
            "MemoryError", "NameError", "UnboundLocalError", "OSError",
            "BlockingIOError", "ChildProcessError", "ConnectionError",
            "BrokenPipeError", "ConnectionAbortedError",
            "ConnectionRefusedError", "ConnectionResetError",
            "FileExistsError", "FileNotFoundError", "InterruptedError",
            "IsADirectoryError", "NotADirectoryError", "PermissionError",
            "ProcessLookupError", "TimeoutError", "ReferenceError",
            "RuntimeError", "NotImplementedError", "RecursionError",
            "StopAsyncIteration", "StopIteration", "SyntaxError",
            "IndentationError", "TabError", "SystemError", "SystemExit",
            "KeyboardInterrupt", "TypeError", "ValueError", "UnicodeError",
            "UnicodeDecodeError", "UnicodeEncodeError",
            "UnicodeTranslateError", "Warning", "UserWarning",
            "RuntimeWarning", "SyntaxWarning", "ImportWarning",
            "PendingDeprecationWarning", "ResourceWarning",
            "EncodingWarning", "ZeroDivisionError", "OverflowError",
        ]
    )
    not_authorized_builtins: List[str] = Field(
        default_factory=lambda: [
            "eval", "exec", "compile", "getattr",
            "setattr", "globals", "input", "exit"
        ]
    )
    sandbox_name: str = Field(default="__sandbox__",
                              description="global name space")
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512
    max_len_output: int = 3000
    max_len_tool_output: int = 3000


def load_config(path_sandbox_config: str):
    """Load the sandbox configuration from a JSON file.

    Args:
        path_sandbox_config: Path of the JSON file.

    Raises:
        ValueError: If the content is not a valid configuration.
        RuntimeError: If the file cannot be read.
    """
    try:
        return SandboxConfig.model_validate_json(
            Path(path_sandbox_config).read_text()
        )
    except ValidationError as e:
        raise ValueError(f"Invalid sandbox config: {e}") from e
    except OSError as e:
        raise RuntimeError(
            f"Impossible configuration read: {path_sandbox_config}"
        ) from e
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid file: {e}") from e
