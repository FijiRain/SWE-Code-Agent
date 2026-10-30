import os
from dotenv import load_dotenv
from pydantic import ValidationError
from src.models.input_data_models import MBPPTaskInput, SWEBenchTaskInput
from src.orchestration.orchestrator import Orchestrator

load_dotenv()


def run_MBPP(task_file: str, output: str,
             model_name: str, provider_url: str) -> None:
    """Load an MBPP task, run the orchestrator, and write the solution."""
    try:
        with open(task_file, 'r') as f:
            task = MBPPTaskInput.model_validate_json(f.read())
    except (FileNotFoundError, OSError, PermissionError) as e:
        raise ValueError(f"Incorrect file '{task_file}':\n{e}") from e
    except ValidationError as e:
        raise ValueError(
            f"Invalid MBPP task config in '{task_file}':\n{e}") from e

    orchestrator = Orchestrator(model_name, provider_url)

    res = orchestrator.complete_task(task)
    if os.path.dirname(output):
        os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(res.model_dump_json(indent=2))


def run_SWE(task_file: str, output: str,
            model_name: str, provider_url: str) -> None:
    """Load a SWE-bench task, run the orchestrator, and write the patch."""
    try:
        with open(task_file, 'r') as f:
            task = SWEBenchTaskInput.model_validate_json(f.read())
    except (FileNotFoundError, OSError, PermissionError) as e:
        raise ValueError(f"Incorrect file '{task_file}':\n{e}") from e
    except ValidationError as e:
        raise ValueError(
            f"Invalid MBPP task config in '{task_file}':\n{e}") from e

    orchestrator = Orchestrator(model_name, provider_url)

    res = orchestrator.complete_task(task)
    if os.path.dirname(output):
        os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(res.model_dump_json(indent=2))
