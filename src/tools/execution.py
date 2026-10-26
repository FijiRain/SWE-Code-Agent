from src.tools.path_utils import resolve_testbed_path, get_testbed_root
import subprocess
import os


def run_command(command: str, workdir: str = ".") -> str:
    timeout = 60
    try:
        working_dir = resolve_testbed_path(workdir)
    except ValueError as e:
        return f"Error: {e}"

    if not working_dir.exists() or not working_dir.is_dir():
        return f"Error: Workdir '{workdir}' is not a valid directory."

    try:
        process = subprocess.run(command, shell=True, cwd=working_dir,
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
    repo = get_testbed_root()
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
    repo = get_testbed_root()
    timeout = 300
    max_size = 15000

    script_path = os.environ.get('EVAL_SCRIPT_PATH')
    if script_path:
        script = resolve_testbed_path(script_path)
    else:
        script = get_testbed_root() / "eval.sh"

    if not script.exists():
        return f"Error: Evaluation script '{script}' not found."

    command = ["/bin/bash", str(script)]
    try:
        process = subprocess.run(command, cwd=repo, capture_output=True,
                                 text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"

    result = f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
    warn_msg = ""
    if len(result) > max_size:
        warn_msg = f"\n...[And {len(result) - max_size} truncated characters]"
        result = result[:max_size]

    return result + warn_msg


def run_mbpp_tests(code: str, test_list: list[str]) -> str:
    pass
