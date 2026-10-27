# flake8: noqa
# uv run python test_provider_errors.py
# Penser a commenter cette ligne dans orchestrator: self.answer = self.run_llm()

from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
from src.orchestration.orchestrator import Orchestrator
from openai import (
    RateLimitError,
    InternalServerError,
    AuthenticationError,
)

load_dotenv()

# 1. On initialise l'orchestrateur (en désactivant le run_llm du constructeur s'il y est encore)
orchestrator = Orchestrator(model="openrouter/free", provider_url="https://openrouter.ai/api/v1")

print("\n--- TEST 1 : Simulation d'un HTTP 429 (Rate Limit) suivi d'un succès ---")
mock_error_429 = RateLimitError(
    message="Quota journalier atteint",
    response=MagicMock(status_code=429),
    body=None,
)
mock_success_429 = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après rotation !"))])

with patch("openai.resources.chat.completions.Completions.create", side_effect=[mock_error_429, mock_success_429]):
    result = orchestrator.query_llm()
    print("Résultat final :", result)
    print("Nombre de retries comptabilisés :", orchestrator.step_retries)

print("\n--- TEST 2 : Simulation d'un HTTP 500 (Panne serveur temporaire) ---")
mock_500 = InternalServerError(
    message="Internal Server Error",
    response=MagicMock(status_code=500),
    body=None,
)
mock_ok_500 = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après reprise du serveur !"))])

with patch("openai.resources.chat.completions.Completions.create", side_effect=[mock_500, mock_ok_500]):
    result = orchestrator.query_llm()
    print("Résultat final :", result)

print("\n--- TEST 3 : Simulation d'un HTTP 401 (Clé invalide / Unauthorized) ---")
mock_401 = AuthenticationError(
    message="Invalid API Key",
    response=MagicMock(status_code=401),
    body=None,
)
mock_ok_401 = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après rotation sur 401 !"))])

with patch("openai.resources.chat.completions.Completions.create", side_effect=[mock_401, mock_ok_401]):
    result = orchestrator.query_llm()
    print("Résultat final :", result)
    print("Nombre total de retries comptabilisés :", orchestrator.step_retries)
