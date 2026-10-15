from dotenv import load_dotenv
import os, requests, json

def get_resp_llm(data: dict) -> str:
    if "error" in data:
        raise RuntimeError(f"Api Error: {data["error"]}")
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndentationError):
        raise RuntimeError(f"No response founded")

load_dotenv(".env")

resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
    json={
        "model": "dots-studio/dots-3-note-preview:free",
        "messages": [{"role": "user", "content": "say hello"}],
        "stop": ["<end_code>", "\nObservation:"],
    },
)
# print(resp.status_code)
# print(json.dumps(resp.json(), indent=4))
print(get_resp_llm(resp.json()))