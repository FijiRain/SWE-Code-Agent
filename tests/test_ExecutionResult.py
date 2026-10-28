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


class MockSandbox:
    def execute(self, code: str) -> ExecutionResult:
        if "final_answer" in code:
            return ExecutionResult(final_answer=code)
        return ExecutionResult(
            stdout="{'success': True, 'output': 'All tests passed!'}"
            )
