from .SandboxConfig import SandboxConfig

from types import ModuleType
from typing import Any, List, Callable, Tuple, Optional, Sequence, Mapping
import builtins


def make_allowed_list_import(authorized_imports: List[str]) -> List[str]:
    allowed_import: List[str] = []
    for name in authorized_imports:
        if name.endswith(".*"):
            ...
        else:
            allowed_import.append(name)


def check_allowed_import(name: str, authorized_import: List[str]) -> bool:
    return name in authorized_import


def make_import(authorized: List[str]) -> Callable[..., ModuleType]:
    def restricted_import(
            name: str,
            globals: Optional[Mapping[str, Any]] = None,
            locals: Optional[Mapping[str, Any]] = None,
            fromlist: Optional[Sequence[str]] = (),
            level: int = 0
            ) -> ModuleType:
        if not check_allowed_import(name, authorized):
            raise ImportError("Error: authorized is not valid import")
        return builtins.__import__(name, globals, locals, fromlist, level)
    return restricted_import
