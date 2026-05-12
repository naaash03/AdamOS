import requests

class OllamaClient:
    def __init__(self, host: str, default_model: str):
        self.host = host.rstrip("/")
        self.default_model = default_model

    def generate(self, prompt: str, system: str = "", model: str | None = None) -> str:
        model = model or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        r = requests.post(f"{self.host}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        return r.json()["response"].strip()