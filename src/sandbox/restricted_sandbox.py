from .SandboxConfig import SandboxConfig

from types import ModuleType
from typing import (Any, List, Callable,
                    Optional, Sequence,
                    Mapping, Dict)
import builtins


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


def build_builtins(config: SandboxConfig) -> Dict:
    safe_builtins = {
        name: getattr(builtins, name)
        for name in config.authorized_builtins
        if hasattr(builtins, name)
    }
    safe_builtins["__import__"] = make_import(config.authorized_imports)
    return safe_builtins
