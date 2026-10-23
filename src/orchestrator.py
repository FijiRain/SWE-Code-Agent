import os
import time
from openai import (OpenAI, APIStatusError,
                    APIConnectionError, APITimeoutError)
from openai.types.chat import ChatCompletionMessageParam

from .key_manager import KeyManager
from .exception import KeyQuotaError, ServerError, FatalError
from .models.input_data_models import MBPPTaskInput, SWEBenchTaskInput
from .models.output_data_models import SolutionOutput, StepMetrics
from .prompts import build_mbpp_sys_prompt, build_mbpp_user_prompt


class Orchestrator:
    """Manage LLM communication, provider resolution, and agent workflow."""

    def __init__(self, model: str, provider_url: str) -> None:
        """Initialize the orchestrator with model, provider, and state."""
        self.model = model
        self.provider_url = provider_url
        self.provider = self.load_provider(provider_url)
        self.key_manager = KeyManager(self.provider)

        self.total_retries = 0
        self.total_time = 0
        self.max_iterations = 0

        self.sandbox = ...  # Anatole ici
        self.sys_prompt = ""
        self.user_prompt = ""
        self.context: list[ChatCompletionMessageParam] = []

        self.step_retries = 0
        self.step_input_tokens = 0
        self.step_output_tokens = 0
        self.step_time = 0.0
        self.all_steps: list[StepMetrics] = []

    def load_provider(self, url: str) -> str:
        """Identify the matching provider environment variable from the URL."""
        format_url = url.lower()
        for key in os.environ:
            if (
                "API_KEY" in key
                and key.rsplit("_API_KEY", 1)[0].lower() in format_url
            ):
                return key
        raise ValueError("Provider not handled")

    def call_api(self) -> str:
        """Send a prompt to the LLM and map API errors to domain exceptions."""
        try:
            with OpenAI(
                base_url=self.provider_url,
                api_key=self.key_manager.get_key()
            ) as client:
                start_time = time.perf_counter()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self.context
                )
                end_time = time.perf_counter()
                self.step_time = (end_time - start_time) * 1000
                if response.usage:
                    self.step_input_tokens = response.usage.prompt_tokens
                    self.step_output_tokens = response.usage.completion_tokens

                return str(response.choices[0].message.content)

        except APIStatusError as e:
            status = e.status_code
            if status in (401, 402, 403, 429):
                raise KeyQuotaError(
                    f"Quota or rate limit exceeded ({status}): {e}") from e
            elif 500 <= status < 600:
                raise ServerError(
                    f"Server error ({status}): {e}") from e
            else:
                raise FatalError(
                    f"Unrecoverable client error ({status}): {e}") from e

        except (APIConnectionError, APITimeoutError) as e:
            raise ServerError(f"Network/connection error: {e}") from e

        except Exception as e:
            raise FatalError(f"Unexpected error: {e}") from e

    def query_llm(self) -> str:
        """Query the LLM with retry logic, key rotation, and error handling."""
        self.step_retries = 0
        self.step_input_tokens = 0
        self.step_output_tokens = 0
        self.step_time = 0

        max_server_retries = 3
        server_retries = 0

        while True:
            try:
                content = self.call_api()
                # In case there's a minute-rate limit on key
                self.key_manager.reset_attempt()
                return content

            except KeyQuotaError:
                self.step_retries += 1
                try:
                    self.key_manager.rotate()
                except ValueError as quota_err:
                    raise KeyQuotaError(
                        "All provider API keys have "
                        "been exhausted.") from quota_err

            except ServerError:
                server_retries += 1
                self.step_retries += 1
                if server_retries > max_server_retries:
                    raise
                time.sleep(5)
                # si erreur de serveur, on peut regarder le status_code
                # renvoyé et dans la classe ServerError
                # determiner le temps auquel la requete HTTP
                # indique qu'il faut retry

            except FatalError:
                raise

    def complete_task(self,
                      task: MBPPTaskInput | SWEBenchTaskInput
                      ) -> SolutionOutput:
        """Execute the agentic loop to solve the task and return solution."""
        if isinstance(task, MBPPTaskInput):
            # Attention il faudra mettre le manual en arg, la c par defaut
            self.sys_prompt = build_mbpp_sys_prompt()
            self.user_prompt = build_mbpp_user_prompt(task)
            self.max_iterations = 10
        else:
            # A implémenter pour SWE, str vide pour Pylance
            self.sys_prompt = ""
            self.user_prompt = ""
            self.max_iterations = 30

        self.context = [{"role": "system", "content": self.sys_prompt},
                        {"role": "user", "content": self.user_prompt}]

        current_iterations = 0  # max iteration 10
        total_input_token = 0 # max 6000, input prompt ≈ 540 tokens
        total_output_token = 0  # max 1500
        total_task_time = 0  # time-out 120s
        solved = False
        while current_iterations < self.max_iterations and not solved:
            current_iterations += 1
            res = self.query_llm()
            self.context.append({"role": "assistant", "content": res})
            # on extrait le code et on l'envoie a la sanbox
            # on recoit la rep de la sandbox : self.context.append({"role": "user", "content": f"Observation:\n{sandbox_output}"}).
            # resumer l'historique ??? a laide
            step = StepMetrics(
                step=current_iterations,
                input_tokens=self.step_input_tokens,
                output_tokens=self.step_output_tokens,
                request_time_ms=self.step_time,
                api_url=self.provider_url,
                model_name=self.model,
                llm_output=res,
                sandbox_input="NON DISPONIBLE",
                sandbox_output="NON DISPONIBLE",
                retries=self.step_retries
            )
            self.all_steps.append(step)
            if solved:
                break
            # Au tour suivant, call_api() renvoie automatiquement tout l'historique mis à jour
        # on renvoie l'objet SolutionOutput validé et tada
        ...
