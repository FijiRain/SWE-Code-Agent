import os
import time
import httpx
from openrouter import OpenRouter
from openrouter.errors import OpenRouterError

from .key_manager import KeyManager
from .exception import KeyQuotaError, ServerError, FatalError


class Orchestrator:
    def __init__(self, model: str, provider_url: str) -> None:
        self.model = model
        self.provider = self.load_provider(provider_url)
        self.key_manager = KeyManager(self.provider)
        self.retries = 0
        self.time = ...
        self.context = ...
        self.sandbox = ...  # Anatole ici
        self.sys_prompt = ...
        # self.answer = self.run_llm()  # pour le test seulement

    def load_provider(self, url: str) -> str:
        format_url = url.lower()
        for key in os.environ:
            if (
                "API_KEY" in key
                and key.rsplit("_API_KEY", 1)[0].lower() in format_url
            ):
                return key
        raise ValueError("Provider not handled")  # attention traceback ?!

    def send_request(self, prompt: str) -> str:
        try:
            with OpenRouter(api_key=self.key_manager.get_key()) as client:
                response = client.chat.send(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                return response.choices[0].message.content

        except OpenRouterError as e:
            status = getattr(e, "status_code", 500)
            if status in (401, 402, 403, 429):
                raise KeyQuotaError(f"Quota or rate limit exceeded ({status}): {e}") from e
            elif 500 <= status < 600:
                raise ServerError(f"Server error ({status}): {e}") from e
            else:
                raise FatalError(f"Unrecoverable client error ({status}): {e}") from e

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ServerError(f"Network/connection error: {e}") from e

        except Exception as e:
            raise FatalError(f"Unexpected error: {e}") from e

    def run_llm(self):
        prompt = (
            "Ceci est juste un test, si tu reçois ce message, répond specifiquement "
            "sous cette forme : Je suis : <nom_du_modele>, je viens de <nom_de_ton_fournissuer> "
            "et j'apprécie le caca."
        )

        max_server_retries = 3
        server_retries = 0

        while True:
            try:
                content = self.send_request(prompt)
                self.key_manager.reset_attempt()  # Requête réussie : on réinitialise les tentatives
                return content

            except KeyQuotaError:
                self.retries += 1
                try:
                    self.key_manager.rotate()
                except ValueError as quota_err:
                    raise KeyQuotaError("All provider API keys have been exhausted.") from quota_err

            except ServerError:
                server_retries += 1
                self.retries += 1
                if server_retries > max_server_retries:
                    raise

                time.sleep(2)

            except FatalError:
                raise
