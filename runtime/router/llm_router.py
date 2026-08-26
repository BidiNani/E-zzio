import json
import urllib.request
import time
from runtime.router.llm_response import LLMResponse


class LLMRouter:
    """
    Routeur d'inférence unifié pour E-zzio.
    Gère Ollama en local et route le Cloud via LiteLLM (localhost:4000).
    """

    def __init__(
        self, default_model="qwen2.5:7b", ollama_url="http://localhost:11434", litellm_url="http://localhost:4000/v1/chat/completions"
    ):
        self.default_model = default_model
        self.ollama_url = ollama_url
        self.litellm_url = litellm_url

    def generate(self, prompt: str, model: str = None) -> LLMResponse:
        target_model = model or self.default_model

        # 1. Tentative d'inférence locale (Ollama)
        response = self._try_ollama(prompt, target_model)
        if response.success:
            return response

        # 2. Tentative de fallback Cloud via LiteLLM Proxy (ex: Gemini/DeepSeek)
        response = self._try_litellm(prompt, target_model)
        if response.success:
            return response

        return LLMResponse(
            text="❌ Erreur critique : Échec de tous les moteurs d'inférence (Ollama local et LiteLLM proxy cloud).",
            model=target_model,
            provider="none",
            latency=0.0,
            success=False,
        )

    def _try_ollama(self, prompt: str, model: str) -> LLMResponse:
        start_time = time.time()
        payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.4, "num_ctx": 4096}}
        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
                latency = time.time() - start_time
                text = result.get("response", "").strip()
                return LLMResponse(text=text, model=model, provider="ollama", latency=latency, success=True)
        except Exception:
            latency = time.time() - start_time
            return LLMResponse(text="", model=model, provider="ollama", latency=latency, success=False)

    def _try_litellm(self, prompt: str, model: str) -> LLMResponse:
        start_time = time.time()
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
        try:
            req = urllib.request.Request(
                self.litellm_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                latency = time.time() - start_time
                text = result["choices"][0]["message"]["content"].strip()
                return LLMResponse(text=text, model=model, provider="litellm-proxy", latency=latency, success=True)
        except Exception:
            latency = time.time() - start_time
            return LLMResponse(text="", model=model, provider="litellm-proxy", latency=latency, success=False)

    def check_health(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False
