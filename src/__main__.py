import os
from dotenv import load_dotenv


class LLM_API:
    def __init__(self) -> None:
        providers = self.load_providers()
        api_keys = ... # un dict qui contiendrait fournisseur: [clés API]

    def load_providers(self) -> list[str]:
        providers = [p for p in os.environ if p.endswith("_API_KEYS")]
        return providers



def main():
    load_dotenv()

    providers = [p for p in os.environ if p.endswith("_API_KEYS")]
    for p in providers:
        groq_api = os.getenv(p).split(",")
        groq_api = [k.strip() for k in groq_api if k.strip()]
        print(groq_api)


main()
