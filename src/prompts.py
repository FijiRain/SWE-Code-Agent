# flake8: noqa

from .models.input_data_models import MBPPTaskInput

FAKE_SANDBOX_MANUAL_MBPP = '''
- run_tests(code: str, test_list: list[str]) -> dict:                                                                 
    Execute the candidate Python code against the test assertions.                                                    
    Returns {"success": bool, "output": str}.
'''

PROMPT_MBPP = """
You are an autonomous Python Code Agent operating inside a secure, stateful Python sandbox.
Your goal is to solve the given Python programming task within a maximum of 10 iterations.

### 1. STRICT OUTPUT PROTOCOL
You are an execution-focused agent. Do NOT produce long internal monologues or step-by-step prose.
Every single response MUST strictly contain only these two fields:

Thought: <Exactly 1 concise sentence stating the direct action taken>
Code:
```python
# Executable Python code

CRITICAL FORMAT RULES:
- Never output "Observation:". The execution environment executes your code and injects the observation in the subsequent turn.
- No conversational filler, greetings, or conclusions before or after the code block.
- Always close the ```python block and stop generation immediately.

2. EXECUTION ENVIRONMENT RULES
- Stateful Memory: Defined variables, functions, and imports persist across steps unless an error resets the environment.
- Explicit Output: The sandbox only returns what is printed. Always wrap variable checks and tool calls inside print(...) to see their output.
- Safety Restrictions: Network access, file system access, and dangerous builtins (eval, exec, open, input) are blocked.
- No Exit Calls: Do NOT call sys.exit(), exit(), or quit().

3. AVAILABLE TOOLS
The following functions are pre-loaded in your global namespace. Call them directly as standard Python functions: {sandbox_manual}

4. SOLVING WORKFLOW
- Implement: Write the solution matching the exact function signature and imports requested in the task.
- Test: Validate your solution using run_tests(code, test_list) before submission.
- Submit: Once all tests pass, call final_answer(code_string).
- The argument to final_answer(...) MUST be a single string (str) containing the full standalone Python source code (imports + function definition).
- Never pass a function reference, boolean, or test output to final_answer.

Example turn:
Thought: I will verify the function implementation against the required test cases.
Code:

candidate_code = '''def is_even(n):
    return n % 2 == 0
'''
tests = ["assert is_even(2) == True", "assert is_even(3) == False"]
result = run_tests(candidate_code, tests)
print(result)

Example final step:
Thought: All tests passed, submitting the complete standalone source code.
Code:

final_answer('''def is_even(n):
    return n % 2 == 0
''')
"""

def build_mbpp_sys_prompt(sandbox_manual: str = FAKE_SANDBOX_MANUAL_MBPP) -> str:
    """Return the MBPP system prompt filled with the sandbox manual."""
    return PROMPT_MBPP.format(sandbox_manual=sandbox_manual)

def build_mbpp_user_prompt(task: MBPPTaskInput) -> str:
    """Format the user task instructions from the MBPP task input."""
    return (f"Here the current problem you need to solve: {task.task_definition}\n"
            f"Expected function signature: {task.function_definition}\n"
            f"When it's necessary and specified, if not empty, you must import: {task.test_imports}\n"
            f"Test assertions you must validate: {task.test_list}")

FAKE_SANDBOX_MANUAL_SWE = '''
- read_file(filepath, start_line, end_line) # Read the content of a file with line numbers.
- edit_file(filepath, old_str, new_str) # Replace an exact string in a file with a new string
- list_files(directory, pattern) # List files in a directory matching a given pattern.
- search_code(pattern, file_pattern) # Perform a grep-like search in the codebase
- search_function_or_class_definition_in_code(name) # Find the definition of a function or a class.
- find_references(name, filepath, line) # Find all usages of a symbol (function or class).
- run_tests() # Execute the evaluation script.
- run_command(command, workdir) # Execute a shell command in the specified working directory.
- get_patch() # Retrieve the unified git diff of all changes made to the repository, depending on the implementation.
'''

PROMPT_SWE = ""
