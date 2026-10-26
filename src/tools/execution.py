from src.tools.path_utils import resolve_testbed_path
import subprocess


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
    pass


def run_swebench_tests() -> str:
    pass


def run_mbpp_tests(code: str, test_list: list[str]) -> str:
    pass
