from .SandboxConfig import SandboxConfig

from types import ModuleType
from typing import (Any, List, Callable,
                    Optional, Sequence,
                    Mapping, Dict,
                    Tuple)
import builtins
import os
import resource
import socket


def valid_module(module: ModuleType,
                 authorized_imports: List[str]) -> ModuleType:
    new_mod = ModuleType(module.__name__)
    for name in dir(module):
        if name.startswith('_'):
            continue

        obj = getattr(module, name)
        if isinstance(obj, ModuleType):
            if not check_allowed_import(obj.__name__, authorized_imports):
                continue
        setattr(new_mod, name, obj)
    return new_mod


def check_allowed_import(name: str, authorized_import: List[str]) -> bool:
    for pattern in authorized_import:
        if pattern.endswith(".*"):
            if name.startswith(pattern[:-1]):
                return True
        elif pattern == name:
            return True
    return False


def make_import(authorized: List[str]) -> Callable[..., ModuleType]:
    """Make restricted builtin __import__"""
    cache: Dict[str, ModuleType] = {}

    def restricted_import(
            name: str,
            globals: Optional[Mapping[str, Any]] = None,
            locals: Optional[Mapping[str, Any]] = None,
            fromlist: Optional[Sequence[str]] = (),
            level: int = 0
            ) -> ModuleType:
        if level != 0 or not check_allowed_import(name, authorized):
            raise ImportError(
                f"Import of '{name}' is not allowed. "
                f"Authorized modules: {', '.join(authorized)}"
            )
        module = builtins.__import__(name, globals, locals, fromlist, level)
        if module.__name__ not in cache:
            cache[module.__name__] = valid_module(module, authorized)
        return cache[module.__name__]
    return restricted_import


def check_path_allowed(path: str, allowed_dir: List[str]) -> bool:
    real = os.path.realpath(path)
    for directory in allowed_dir:
        base = os.path.realpath(directory)
        if os.path.commonpath([real, base]) == base:
            return True
    return False


def make_open(allowed_dir: List[str]) -> Callable[..., Any]:
    """make builtin restricted open builtin"""
    def restricted_open(file, *args, **kwargs):
        if not isinstance(file, (str, bytes, os.PathLike)):
            raise PermissionError("open() only accepts file paths")
        path = os.fsdecode(file)
        if not check_path_allowed(path, allowed_dir):
            raise PermissionError(
                f"Access to '{path}' is not allowed. "
                f"Allowed directories (use absolute paths): "
                f"{', '.join(allowed_dir)}"
            )
        return builtins.open(file, *args, **kwargs)
    return restricted_open


def build_builtins(config: SandboxConfig) -> Dict:
    """ Create authorize builtin"""
    safe_builtins = {
        name: getattr(builtins, name)
        for name in config.authorized_builtins
        if hasattr(builtins, name)
    }
    safe_builtins["__import__"] = make_import(config.authorized_imports)
    safe_builtins["open"] = make_open(config.allowed_directories)
    return safe_builtins


def apply_memory_restricted(max_memory_mb: int) -> None:
    """Cap the address space of the current process."""
    limits = max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limits, limits))


def truncke_output(output: str, max_len: int) -> Tuple[str, bool]:
    """Truncke output with max size, return new size of new output and add
    message to inform trucatded output
    Return :
        - new output -> str
        - if output has truncked -> bool
    """
    len_output = len(output)
    is_truncke = False
    if len_output > max_len:
        new_output = output[:max_len]
        len_new_output = len(new_output)
        new_output += (
                "\n\n[output truncated: showing "
                f"first {len_new_output} of "
                f"{len_output} characters]"
        )
        is_truncke = True
        return (new_output, is_truncke)
    return (output, False)


def restricted_conn() -> None:
    def refuse(*args, **kwargs) -> None:
        raise PermissionError("Network access is disabled in the sandbox")

    class BlockedSocket(socket.socket):
        def __init__(self, *args, **kwargs):
            refuse()

    socket.socket = BlockedSocket
    socket.SocketType = BlockedSocket
    for name in ("create_connection", "create_server", "fromfd",
                 "getaddrinfo", "gethostbyname", "gethostbyname_ex",
                 "gethostbyaddr", "getnameinfo"):
        setattr(socket, name, refuse)
