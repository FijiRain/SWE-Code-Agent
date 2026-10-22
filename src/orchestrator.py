import os
import time
from openai import (OpenAI, APIStatusError,
                    APIConnectionError, APITimeoutError)

from .key_manager import KeyManager
from .exception import KeyQuotaError, ServerError, FatalError
from .models.input_data_models import MBPPTaskInput, SWEBenchTaskInput
from .models.output_data_models import SolutionOutput
from .react_loop import ReactLoop


class Orchestrator:
    """Manage LLM communication, provider resolution, and agent workflow."""

    def __init__(self, model: str, provider_url: str) -> None:
        """Initialize the orchestrator with model, provider, and state."""
        self.model = model
        self.provider_url = provider_url
        self.provider = self.load_provider(provider_url)
        self.key_manager = KeyManager(self.provider)

        self.step_retries = 0
        self.step_input_tokens = 0
        self.step_output_tokens = 0
        self.step_time = 0.0
        self.self_list = []

        self.total_retries = 0
        self.total_time = 0

        self.context = ...
        self.sandbox = ...  # Anatole ici
        self.sys_prompt = ...
        self.answer = self.query_llm()  # pour le test seulement

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

    def call_api(self, prompt: str) -> str:
        """Send a prompt to the LLM and map API errors to domain exceptions."""
        try:
            with OpenAI(
                base_url=self.provider_url,
                api_key=self.key_manager.get_key()
            ) as client:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
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

        prompt = ("Ceci est juste un test, si tu reçois ce message, "
                  "répond specifiquement sous cette forme : "
                  "Je suis : <nom_du_modele>, je viens de "
                  "<nom_de_ton_fournisseur> et j'apprécie le caca.")

        max_server_retries = 3
        server_retries = 0

        while True:
            try:
                content = self.call_api(prompt)
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
        loop = ReactLoop(task)
        # prepa le prompt avec la consigne de task "task_definition"
        # lance une boucle while iterations < max_iterations:
        # a chaque tour on applique le pattern ReAct et
        # on fait un objet StepMetrics
        # on renvoie l'objet SolutionOutput validé et tada
        ...
