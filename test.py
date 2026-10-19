from dotenv import load_dotenv
import os

load_dotenv()

providers = [p.replace("_API_KEYS", "").lower()
             for p in os.environ if "API" in p]
print(providers)
url = "https://groq.api/v1"

