from dotenv import load_dotenv
from pydantic import ValidationError
from src.models.input_data_models import MBPPTaskInput
from src.orchestrator import Orchestrator

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
    # print(orchestrator.answer)  # c'est un test

    res = orchestrator.complete_task(task)
    print(res)
    # A la fin ouvrir le fichier au chemin output et faire
    # un model_dump_json() pour ecrire res dans un fichier solution.json


def run_SWE():
    """Load a SWE-bench task, run the orchestrator, and write the patch."""
    # TODO
    ...


# uv run python -m agent_mbpp
# --task-file ../cache/mbpp_task.json
# --output ../cache/mbpp_solution.json
# --model-name "model/name"
# --provider-url "https://provider.api/v1"

# pour test
# uv run python -m agent_mbpp
# --task-file test_mbpp_task.json
# --output ../cache/mbpp_solution.json
# --model-name "openrouter/free"
# --provider-url "https://openrouter.api/v1"
