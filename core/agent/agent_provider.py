"""E-ZZIO Coding Agent — Unified Provider Adapter (Cloud Gemini vs Local Ollama/Ornith/Qwen)."""
from __future__ import annotations
import json
import urllib.request
from typing import Dict, Any
from core.cloud_brain_broker import cloud_chat

class AgentProviderAdapter:
    def __init__(self, backend: str = "cloud_gemini", local_model: str = "ornith-1.5:9b"):
        self.backend = backend
        self.local_model = local_model
        self.ollama_url = "http://localhost:11434/api/generate"

    def chat(self, text: str, system_prompt: str = "") -> Dict[str, Any]:
        if self.backend == "cloud_gemini":
            return cloud_chat(text=text, system_prompt=system_prompt, speed="fast")
        
        elif self.backend == "local_ollama":
            payload = {
                "model": self.local_model,
                "prompt": f"System: {system_prompt}\n\nUser: {text}\n\nAssistant:",
                "stream": False
            }
            try:
                req = urllib.request.Request(
                    self.ollama_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                # Timeout élargi à 180s pour laisser respirer le modèle local sur les gros contextes
                with urllib.request.urlopen(req, timeout=180) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    data = json.loads(raw)
                    response_text = data.get("response", "").strip()
                    return {
                        "response": response_text,
                        "ok": True,
                        "source": f"Local Ollama ({self.local_model})"
                    }
            except Exception as exc:
                return {
                    "response": f"[FAIL-CLOSED] Erreur Ollama local ({self.local_model}) : {exc}",
                    "ok": False
                }
        else:
            return {"response": "[FAIL-CLOSED] Backend agent inconnu.", "ok": False}
