import requests
import time
from typing import Dict, Any


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    def generate(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse avec Ollama
        """
        start_time = time.time()

        # Nettoyer les kwargs
        options = {}
        if "num_ctx" in kwargs:
            options["num_ctx"] = kwargs["num_ctx"]
        if "num_predict" in kwargs:
            options["num_predict"] = kwargs["num_predict"]
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]

        # Payload Ollama
        payload = {"model": model, "prompt": prompt, "stream": False, "options": options}

        try:
            # Appel API
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=kwargs.get("timeout", 120))
            response.raise_for_status()

            # Parse response
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            return {"response": data.get("response", ""), "latency_ms": latency_ms}

        except Exception as e:
            return {"response": f"Erreur Ollama: {str(e)}", "latency_ms": (time.time() - start_time) * 1000}
