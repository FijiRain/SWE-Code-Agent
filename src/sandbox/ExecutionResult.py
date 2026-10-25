"""Result model of a sandbox execution and the final answer signal."""
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Result of running one code snippet in the sandbox."""

    stdout: str = Field(
        default="",
        description=(
            "Everything the code printed (partial if timed out, ends with a "
            "notice if truncated)"
        )
    )
    error: str = Field(
        default="",
        description=(
            "Exception message if the code crashed"
        )
    )
    timed_out: bool = Field(
        default=False,
        description=(
            "True if the code was killed by the timeout"
        )
    )
    truncated: bool = Field(
        default=False,
        description=(
            "True if stdout was cut for size"
        )
    )
    final_answer: str | None = Field(
        default=None,
        description=(
            "Argument passed to final_answer(), if called"
        )
    )


class FinalAnswerSignal(BaseException):
    """Raised by final_answer() to stop the running code.

    It derives from BaseException so that a bare ``except Exception`` in
    the executed code does not catch it.
    """

    def __init__(self, value) -> None:
        """Store the value passed to final_answer()."""
        self.value = value
