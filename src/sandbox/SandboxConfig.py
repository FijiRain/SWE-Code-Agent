from pydantic import BaseModel, Field, ValidationError
from typing import List
from pathlib import Path


class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions.
        Uses allowlist approach: only imports in authorized_imports
        are allowed.
        Everything else is blocked by default.
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
            "/testbed", "/tmp/agent"
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
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512


def load_config(path_sandbox_config: str):
    """Load sandbox config from json file"""
    try:
        return SandboxConfig.model_validate_json(
            Path(path_sandbox_config).read_text()
        )
    except ValidationError as e:
        raise ValueError("Config Error") from e
    except OSError as e:
        raise RuntimeError(
            f"Impossible configuration read: {path_sandbox_config}"
        ) from e
    except UnicodeDecodeError as e:
        raise ValueError("invalid file") from e
