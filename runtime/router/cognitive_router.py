from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parents[2] / "secrets" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


class CognitiveRouter:
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.gemini_client = None
        self.cloud_failures = 0
        self._init_gemini()

    def _init_gemini(self):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API")
        if api_key:
            try:
                from google import genai

                self.gemini_client = genai.Client(api_key=api_key)
            except Exception:
                pass

    def route_query(self, prompt: str, target: str = "auto", model_hint: str = "qwen2.5-coder:7b") -> str:
        # Tentative cloud si demandé ou prioritaire (si pas de black-listing par erreurs consécutives)
        if (target == "cloud" or (target == "auto" and len(prompt) > 2500)) and self.gemini_client and self.cloud_failures < 3:
            try:
                response = self.gemini_client.models.generate_content(model="gemini-2.5-pro", contents=prompt)
                return response.text
            except Exception:
                self.cloud_failures += 1
                # Fallback automatique vers local en cas d'échec cloud

        # Exécution locale via Ollama
        payload = json.dumps({"model": model_hint, "prompt": prompt, "stream": False}).encode("utf-8")

        req = urllib.request.Request(
            f"{self.ollama_host}/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except Exception as e:
            raise RuntimeError(f"Échec critique de la passerelle locale et repli cloud impossible : {e}")
