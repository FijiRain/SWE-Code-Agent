import os
from pathlib import Path


def get_testbed_root() -> Path:
    """Return the resolved testbed root directory from TESTBED_PATH or cwd."""
    value = os.environ.get("TESTBED_PATH")
    if value and value.strip():
        path = Path(value).resolve()
    else:
        path = Path.cwd().resolve()
    return path


def to_display_path(file: Path) -> str:
    """Format a path as /testbed/<relative_path> for LLM and Docker
    consistency."""
    root = get_testbed_root()
    try:
        rel = file.resolve().relative_to(root)
        if str(rel) == ".":
            return "/testbed"
        return f"/testbed/{rel}"
    except ValueError:
        return str(file.resolve())


def resolve_testbed_path(user_path: str) -> Path:
    """Resolve a path relative to the testbed root and validate boundaries.

    Args:
        user_path: Relative or absolute path string within the testbed.

    Returns:
        The resolved Path object inside the testbed root.

    Raises:
        ValueError: If the resolved path escapes the testbed root.
    """
    testbed_root = get_testbed_root()

    user_str = str(user_path).strip()

    #  If path is "/testbed" or "/testbed/...", map it to testbed_root
    if user_str == "/testbed" or user_str.startswith("/testbed/"):
        rel = user_str.removeprefix("/testbed").lstrip("/")
        path = testbed_root / rel
    #  If relative path, anchor to testbed_root
    elif not Path(user_str).is_absolute():
        path = testbed_root / user_str
    #  If raw absolute path (e.g. host /tmp path during tests)
    else:
        path = Path(user_str)

    resolved = path.resolve()
    if not resolved.is_relative_to(testbed_root):
        raise ValueError("Given path is not relative to testbed root")
    return resolved
