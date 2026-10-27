"""Restrictions applied to the worker process of the sandbox."""
from ..models.SandboxConfig import SandboxConfig

from types import ModuleType
from typing import (Any, List, Callable,
                    Optional, Sequence,
                    Mapping, Dict,
                    Tuple)
import builtins
import os
import resource
import socket
import sys


def valid_module(module: ModuleType,
                 authorized_imports: List[str]) -> ModuleType:
    """Return a filtered copy of a module.

    Private names (starting with "_") and sub-modules that are not
    authorized are removed, so that the code cannot reach e.g. os
    through an allowed module.

    Args:
        module: Module to filter.
        authorized_imports: Allowed module names or "package.*" patterns.
    """
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
    """Return True if a module name matches an authorized pattern.

    A pattern is either an exact module name or "package.*", which
    matches every sub-module of the package.
    """
    for pattern in authorized_import:
        if pattern.endswith(".*"):
            if name.startswith(pattern[:-1]):
                return True
        elif pattern == name:
            return True
    return False


def make_import(authorized: List[str]) -> Callable[..., ModuleType]:
    """Build a restricted __import__ builtin.

    Only absolute imports of authorized modules are allowed, and the
    imported modules are filtered with valid_module() (results are cached).

    Args:
        authorized: Allowed module names or "package.*" patterns.
    """
    cache: Dict[str, ModuleType] = {}

    def restricted_import(
            name: str,
            globals: Optional[Mapping[str, Any]] = None,
            locals: Optional[Mapping[str, Any]] = None,
            fromlist: Optional[Sequence[str]] = (),
            level: int = 0
            ) -> ModuleType:
        """Import a module if it is authorized, raise ImportError if not."""
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
    """Return True if a path is inside one of the allowed directories.

    Symbolic links and ".." are resolved before the check.
    """
    real = os.path.realpath(path)
    for directory in allowed_dir:
        base = os.path.realpath(directory)
        if os.path.commonpath([real, base]) == base:
            return True
    return False


def make_open(allowed_dir: List[str]) -> Callable[..., Any]:
    """Build a restricted open builtin.

    Args:
        allowed_dir: Directories in which files can be opened.
    """
    def restricted_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        """Open a file, raise PermissionError if it is not allowed."""
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
    """Build the builtins of the sandbox namespace.

    Keep only the authorized builtins and replace __import__ and open by
    their restricted versions.

    Args:
        config: Sandbox configuration.
    """
    safe_builtins = {
        name: getattr(builtins, name)
        for name in config.authorized_builtins
        if hasattr(builtins, name)
    }
    safe_builtins["__import__"] = make_import(config.authorized_imports)
    safe_builtins["open"] = make_open(config.allowed_directories)
    return safe_builtins


def apply_memory_restricted(max_memory_mb: int) -> None:
    """Cap the address space of the current process (enforced on Linux only).

    If the system refuses (for example macOS), print a warning and go on
    without a memory limit.
    """
    limit = max_memory_mb * 1024 * 1024
    try:
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard != resource.RLIM_INFINITY:
            limit = min(limit, hard)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError) as e:
        print(f"Warning: memory limit not applied ({e})", file=sys.stderr)


def truncke_output(output: str, max_len: int) -> Tuple[str, bool]:
    """Cut an output to max_len characters.

    When the output is cut, a notice with the original length is added at
    the end.

    Args:
        output: Text to truncate.
        max_len: Maximum number of characters kept.

    Returns:
        The new output and True if it was truncated.
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
    """Disable network access in the current process.

    Socket creation and name resolution functions of the socket module
    are replaced by functions that raise PermissionError.
    """
    def refuse(*args: Any, **kwargs: Any) -> None:
        """Raise PermissionError for any network access."""
        raise PermissionError("Network access is disabled in the sandbox")

    class BlockedSocket(socket.socket):
        """Socket class that cannot be instantiated."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Refuse the creation of the socket."""
            refuse()

    socket.socket = BlockedSocket  # type: ignore[misc]
    socket.SocketType = BlockedSocket
    for name in ("create_connection", "create_server", "fromfd",
                 "getaddrinfo", "gethostbyname", "gethostbyname_ex",
                 "gethostbyaddr", "getnameinfo"):
        setattr(socket, name, refuse)
