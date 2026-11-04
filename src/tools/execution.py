from src.tools.path_utils import (resolve_testbed_path, get_testbed_root,
                                  to_display_path)
import subprocess
import os
import re
import sys
import json


def run_command(command: str, workdir: str = ".") -> str:
    """Execute a shell command inside the testbed working directory.

    Args:
        command: Shell command string to execute.
        workdir: Working directory relative to the testbed root.

    Returns:
        Formatted string containing exit code, STDOUT, and STDERR, or an
        error message if execution fails or times out.
    """
    timeout = 60
    container_id = os.environ.get("SWE_CONTAINER_ID")
    testbed_env = os.environ.get("TESTBED_PATH")

    if not container_id and not (testbed_env and testbed_env.strip()):
        return ("Error: Neither SWE_CONTAINER_ID nor TESTBED_PATH is set. "
                "Refusing to execute command on host.")

    try:
        working_dir = resolve_testbed_path(workdir)
    except ValueError as e:
        return f"Error: {e}"
    if not working_dir.exists() or not working_dir.is_dir():
        return f"Error: Workdir '{workdir}' is not a valid directory."

    if container_id:
        container_workdir = to_display_path(working_dir)
        cmd_args = [
            "docker", "exec", "-w", container_workdir,
            container_id, "/bin/bash", "-c", command
        ]
        run_cwd = None
    else:
        cmd_args = ["/bin/bash", "-c", command]
        run_cwd = working_dir

    try:
        process = subprocess.run(cmd_args, cwd=run_cwd,
                                 capture_output=True, text=True,
                                 timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command {e}"

    return (f"Exit code: {process.returncode}\n"
            f"STDOUT:\n{process.stdout}\n"
            f"STDERR:\n{process.stderr}")


def get_patch() -> str:
    """Generate a unified git diff of changes in the testbed repository.

    Returns:
        The git diff output as a string, or an error message if git diff
        fails or times out.
    """
    try:
        repo = get_testbed_root()
    except ValueError as e:
        return f"Error: {e}"
    timeout = 60
    command = ["git", "-c", "core.fileMode=false", "diff"]
    try:
        process = subprocess.run(command, cwd=repo, capture_output=True,
                                 text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"

    if process.returncode != 0:
        error_msg = process.stderr.strip() or ("git diff failed with non-zero "
                                               "exit code")
        return f"Error: {error_msg}"
    return process.stdout


def run_swebench_tests() -> str:
    """Run the SWE-bench evaluation script inside the testbed repository.

    Returns:
        Captured STDOUT and STDERR from the evaluation script (only the
        last 2000 characters, where the test summary is), or an error
        message string.
    """
    try:
        repo = get_testbed_root()
    except ValueError as e:
        return f"Error: {e}"
    timeout = 300
    # The sandbox prints only the first 4000 characters of stdout:
    # stay well below it so the test summary at the end stays visible
    # without filling the provider tokens/minute budget
    max_size = 2000
    container_id = os.environ.get("SWE_CONTAINER_ID")
    testbed_env = os.environ.get("TESTBED_PATH")

    if not container_id and not (testbed_env and testbed_env.strip()):
        return ("Error: Neither SWE_CONTAINER_ID nor TESTBED_PATH is set. "
                "Refusing to execute command on host.")

    script_path = os.environ.get('EVAL_SCRIPT_PATH')
    if script_path:
        try:
            script = resolve_testbed_path(script_path)
        except ValueError as e:
            return f"Error: {e}"

    else:
        script = repo / "eval.sh"

    if not script.exists():
        return f"Error: Evaluation script '{script}' not found."

    if container_id:
        cmd_args = ["docker", "exec", "-w", "/testbed", container_id,
                    "/bin/bash", to_display_path(script)]
        run_cwd = None
    else:
        cmd_args = ["/bin/bash", str(script)]
        run_cwd = repo

    try:
        process = subprocess.run(cmd_args, cwd=run_cwd, capture_output=True,
                                 text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command {e}"

    # Nested bash xtrace lines ("++ ...", conda activation) are pure noise
    stderr = "\n".join(line for line in process.stderr.splitlines()
                       if not re.match(r"\+{2,} ", line))
    result = (f"Exit code: {process.returncode}\n"
              f"STDOUT:\n{process.stdout}\n"
              f"STDERR:\n{stderr}")
    warn_msg = ""
    if len(result) > max_size:
        truncated = len(result) - max_size
        warn_msg = f"...[Truncated {truncated} characters from start]...\n"
        result = (f"Exit code: {process.returncode}\n" + warn_msg +
                  result[-max_size:])
    return result


def run_mbpp_tests(code: str, test_list: list[str]) -> str:
    """Execute candidate Python code against a list of MBPP test assertions.

    Args:
        code: Candidate Python source code to test.
        test_list: List of assertion statements to run against the code.

    Returns:
        A JSON-formatted string with keys 'success' (bool) and 'output' (str).
    """
    timeout = 30

    script_lines = [code, "\n"]
    for test in test_list:
        script_lines.append(test)
    full_script = "\n".join(script_lines)
    command = [sys.executable, "-c", full_script]
    try:
        process = subprocess.run(command, capture_output=True,
                                 text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        success = False
        output = f"Execution timed out after {timeout} seconds."
        return json.dumps({"success": success, "output": output})

    if process.returncode == 0:
        success = True
        output = f"All {len(test_list)} assertions passed."
    else:
        success = False
        output = process.stderr.strip()

    return json.dumps({"success": success, "output": output})
