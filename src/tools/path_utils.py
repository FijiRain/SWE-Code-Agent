import os
from pathlib import Path

def get_testbed_root() -> Path:
    value = os.environ.get("TESTBED_PATH")
    if value and value.strip():
        path = Path(value).resolve()
    else:
        path = Path.cwd().resolve()
    return path


def resolve_testbed_path(user_path: str) -> Path:
    testbed_root = get_testbed_root()
    path = Path(user_path)
    if not path.is_absolute():
        path = testbed_root / path

    resolved = path.resolve()
    if not resolved.is_relative_to(testbed_root):
        raise ValueError("Given path is not relative to testbed root")
    return resolved
