import os
import time
import requests
from ..schemas import ModelRequest, ModelResponse


class GeminiProvider:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def execute(self, model: str, req: ModelRequest) -> ModelResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY non configurée.")

        start_time = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        contents = [{"parts": [{"text": req.prompt}]}]
        if req.system_prompt:
            contents.insert(0, {"role": "user", "parts": [{"text": f"System: {req.system_prompt}"}]})

        payload = {"contents": contents}
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        latency = (time.time() - start_time) * 1000

        content = data["candidates"][0]["content"]["parts"][0]["text"]

        return ModelResponse(content=content, model_used=model, provider_used="gemini", latency_ms=latency)
