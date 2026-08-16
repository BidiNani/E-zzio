import requests
import time
from typing import Dict, Any
from ..schemas import ModelRequest, ModelResponse

class OllamaProvider:
    def __init__(self, host: str = "http://127.0.0.1:11434"):
        self.host = host

    def execute(self, model: str, req: ModelRequest, keep_alive: str = "5m") -> ModelResponse:
        start_time = time.time()
        payload = {
            "model": model,
            "prompt": req.prompt,
            "system": req.system_prompt or "",
            "stream": False,
            "keep_alive": keep_alive
        }
        
        res = requests.post(f"{self.host}/api/generate", json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        latency = (time.time() - start_time) * 1000

        return ModelResponse(
            content=data.get("response", ""),
            model_used=model,
            provider_used="ollama",
            tokens_evaluated=data.get("prompt_eval_count", 0),
            tokens_generated=data.get("eval_count", 0),
            latency_ms=latency
        )
