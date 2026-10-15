- set API, to get the code of ochestration par
- set REPL interface (second phase)
- Run code wiht stdout capture
- Manage timeout
- Call run_tests via MCP
- Create Final answer function
- add Sand box Manual


see with orchestration:
- Se mettre daccor sur la classe renvoyer
- Output:
``` python
class ExecutionResult(BaseModel):
    """Result of running one code snippet in the sandbox."""

    stdout: str = Field(
        default="",
        description="Everything the code printed (partial if timed out, ends with a notice if truncated)",
    )
    error: str = Field(default="", description="Exception message if the code crashed")
    timed_out: bool = Field(default=False, description="True if the code was killed by the timeout")
    truncated: bool = Field(default=False, description="True if stdout was cut for size")
    final_answer: str | None = Field(default=None, description="Argument passed to final_answer(), if called")
```
- Input: 
```python
code: str # -> This code is format on str 
# code = "result = run_test_(my_code, tests)\n print(result)"
```

see with mcp
A voir avec alix pour savoir si je m'occupe ou non de la partie mcp client

