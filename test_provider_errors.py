# flake8: noqa
# uv run python test_provider_errors.py
# Penser a commenter cette ligne dans orchestrator: self.answer = self.run_llm()

from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
from src.orchestrator import Orchestrator                                                                             
from openrouter.errors import (
    TooManyRequestsResponseError,
    InternalServerResponseError,
    UnauthorizedResponseError,
)               

load_dotenv()
                                                                                                                        
# 1. On initialise l'orchestrateur (en désactivant le run_llm du constructeur s'il y est encore)                      
orchestrator = Orchestrator(model="openrouter/free", provider_url="https://openrouter.ai/api/v1")                     
                                                                                                                        
print("\n--- TEST 1 : Simulation d'un HTTP 429 (Rate Limit) suivi d'un succès ---")                                   
# On simule : 1er appel = 429, 2ème appel = Réponse valide                                                            
mock_error = TooManyRequestsResponseError(                                                                            
    data=MagicMock(error=MagicMock(message="Quota journalier atteint")),                                              
    raw_response=MagicMock(status_code=429, text="Rate limit exceeded")                                               
)                                                                                                                     
mock_success = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après rotation !"))])                   
                                                                                                                        
with patch("openrouter.chat.Chat.send", side_effect=[mock_error, mock_success]):                            
    result = orchestrator.run_llm()                                                                                   
    print("Résultat final :", result)                                                                                 
    print("Nombre de retries comptabilisés :", orchestrator.retries)                                                  
                                                                                                                        
print("\n--- TEST 2 : Simulation d'un HTTP 500 (Panne serveur temporaire) ---")                                       
mock_500 = InternalServerResponseError(                                                                               
    data=MagicMock(),                                                                                                 
    raw_response=MagicMock(status_code=500, text="Internal Server Error")                                             
)                                                                                                                     
mock_ok = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après reprise du serveur !"))])              
                                                                                                                        
with patch("openrouter.chat.Chat.send", side_effect=[mock_500, mock_ok]):                                   
    result = orchestrator.run_llm()                                                                                   
    print("Résultat final :", result)

print("\n--- TEST 3 : Simulation d'un HTTP 401 (Clé invalide / Unauthorized) ---")
mock_401 = UnauthorizedResponseError(
    data=MagicMock(error=MagicMock(message="User not found (invalid API key)")),
    raw_response=MagicMock(status_code=401, text="Unauthorized"),
)
mock_ok_401 = MagicMock(choices=[MagicMock(message=MagicMock(content="Succès après rotation sur 401 !"))])

with patch("openrouter.chat.Chat.send", side_effect=[mock_401, mock_ok_401]):
    result = orchestrator.run_llm()
    print("Résultat final :", result)
    print("Nombre total de retries comptabilisés :", orchestrator.retries)
