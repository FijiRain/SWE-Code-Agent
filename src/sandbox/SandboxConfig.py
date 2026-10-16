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
