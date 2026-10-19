import os

from .key_manager import KeyManager
from openrouter import OpenRouter


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
        self.answer = self.run_llm()  # pour le test seulement

    def load_provider(self, url: str) -> str:
        format_url = url.lower()
        for key in os.environ:
            if (
                "API_KEY" in key
                and key.rsplit("_API_KEY", 1)[0].lower() in format_url
            ):
                return key
        raise ValueError("Provider not handled")

    def run_llm(self):
        while True:
            try:
                prompt = ("Ceci est juste un test, si tu reçois ce message, répond specifiquement sous cette forme : Je suis : <nom_du_modele>, je viens de <nom_de_ton_fournissuer> et j'apprécie le caca.")

                with OpenRouter(api_key=self.key_manager.get_key()) as client:
                    response = client.chat.send(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                    )

                    self.key_manager.reset_attempt() # Parce que ca a fonctionné donc on peut repartir sur la clé courante
                    return (response.choices[0].message.content)
            except Exception as e:
                print(f"Erreur API ({e}), rotation de clé...")
                self.retries += 1
                self.key_manager.rotate()
