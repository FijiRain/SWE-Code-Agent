import os


class KeyManager:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.keys = self.load_api_keys()
        if not self.keys:
            raise ValueError(f"No API keys found for provider {self.provider}")
        self.current_index = 0
        self.attempts = 0

    def load_api_keys(self) -> list[str]:
        return [k.strip() for k in os.environ[self.provider].split(",")
                if k.strip()]

    def get_key(self) -> str:
        return self.keys[self.current_index]

    def rotate(self) -> None:
        self.current_index = (self.current_index + 1) % len(self.keys)
        self.attempts += 1
        if self.attempts >= len(self.keys):
            raise ValueError("All keys have exceeded their quota")

    def reset_attempt(self) -> None:
        self.attempts = 0
