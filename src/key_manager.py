import os


class KeyManager:
    """Manage API keys and handle key rotation for a given provider."""

    def __init__(self, provider: str) -> None:
        """Initialize the key manager with keys for the specified provider."""
        self.provider = provider
        self.keys = self.load_api_keys()
        if not self.keys:
            raise ValueError(f"No API keys found for provider {self.provider}")
        self.current_index = 0
        self.attempts = 0

    def load_api_keys(self) -> list[str]:
        """Load and sanitize API keys from the provider environment var."""
        return [k.strip() for k in os.environ[self.provider].split(",")
                if k.strip()]

    def get_key(self) -> str:
        """Return the currently active API key."""
        return self.keys[self.current_index]

    def rotate(self) -> None:
        """Rotate to the next API key or raise if all are exhausted."""
        self.current_index = (self.current_index + 1) % len(self.keys)
        self.attempts += 1
        if self.attempts >= len(self.keys):
            raise ValueError("All keys have exceeded their quota")

    def reset_attempt(self) -> None:
        """Reset the consecutive failure attempts counter upon success."""
        self.attempts = 0
