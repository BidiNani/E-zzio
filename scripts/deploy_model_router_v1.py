from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTER_DIR = ROOT / "runtime" / "model_router"
PROVIDERS_DIR = ROUTER_DIR / "providers"

ROUTER_DIR.mkdir(parents=True, exist_ok=True)
PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)

files = {
    # 1. Config Catalog
    "runtime/model_router/config.json": """{
  "ollama_host": "http://127.0.0.1:11434",
  "default_keep_alive": "5m",
  "catalog": {
    "qwen3:8b": {
      "provider": "ollama",
      "capabilities": ["chat", "general", "orchestration"],
      "max_complexity": "medium"
    },
    "qwen2.5-coder:7b": {
      "provider": "ollama",
      "capabilities": ["code", "scripting"],
      "max_complexity": "medium"
    },
    "gemma4e4b:latest": {
      "provider": "ollama",
      "capabilities": ["vision", "ocr"],
      "max_complexity": "low"
    },
    "gemini-3.6-flash": {
      "provider": "gemini",
      "capabilities": ["chat", "code", "vision", "general"],
      "max_complexity": "high"
    },
    "gemini-2.5-pro": {
      "provider": "gemini",
      "capabilities": ["architecture", "reasoning", "complex_code"],
      "max_complexity": "critical"
    },
    "Qwen3-Coder-30B-A3B": {
      "provider": "llama_cpp",
      "capabilities": ["complex_code", "refactoring"],
      "model_path": "models/gguf/code/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
    }
  }
}
""",
    # 2. Schemas
    "runtime/model_router/schemas.py": """from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class ModelRequest:
    prompt: str
    task: str = "general"               # general, code, vision, reasoning
    complexity: str = "low"            # low, medium, high, critical
    latency: str = "normal"             # fast, normal
    budget: str = "local_first"         # local_first, cloud_first, offline_only
    system_prompt: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelResponse:
    content: str
    model_used: str
    provider_used: str
    tokens_evaluated: int = 0
    tokens_generated: int = 0
    latency_ms: float = 0.0
    fallback_applied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
""",
    # 3. Telemetry / Audit
    "runtime/model_router/telemetry.py": r"""import json
import time
from pathlib import Path
from datetime import datetime, timezone
from .schemas import ModelResponse

class RouterTelemetry:
    def __init__(self, audit_dir: Optional[Path] = None):
        self.audit_dir = audit_dir or Path(r"G:\AI\E-zzio\runtime\audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_dir / "model_usage.jsonl"

    def log_usage(self, agent_id: str, request_task: str, response: ModelResponse) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_id,
            "task": request_task,
            "model": response.model_used,
            "provider": response.provider_used,
            "tokens_in": response.tokens_evaluated,
            "tokens_out": response.tokens_generated,
            "latency_ms": round(response.latency_ms, 2),
            "fallback": response.fallback_applied
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\\n")
        except Exception:
            pass
""",
    # 4. Health Check
    "runtime/model_router/health.py": r"""import requests
import os
from pathlib import Path
from typing import Dict, Any

class ModelHealthChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_host = config.get("ollama_host", "http://127.0.0.1:11434")

    def check_ollama(()) -> bool:
        try:
            res = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def check_gemini(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def check_gguf_path(self, relative_path: str) -> bool:
        full_path = Path(r"G:\AI\E-zzio") / relative_path
        return full_path.exists()
""",
    # 5. Selector (Decision Engine)
    "runtime/model_router/selector.py": """from typing import List, Dict, Any
from .schemas import ModelRequest

class ModelSelector:
    def __init__(self, catalog: Dict[str, Any]):
        self.catalog = catalog

    def select_cascade(self, req: ModelRequest) -> List[str]:
        cascade = []

        if req.budget == "offline_only":
            if req.task == "code":
                cascade.extend(["qwen2.5-coder:7b", "qwen3:8b", "Qwen3-Coder-30B-A3B"])
            elif req.task == "vision":
                cascade.extend(["gemma4e4b:latest"])
            else:
                cascade.extend(["qwen3:8b", "qwen2.5-coder:7b"])
            return cascade

        # Règle local_first / cloud_first
        if req.complexity in ["high", "critical"] and req.budget != "offline_only":
            cascade.extend(["gemini-2.5-pro", "gemini-3.6-flash"])
            if req.task == "code":
                cascade.append("qwen2.5-coder:7b")
            else:
                cascade.append("qwen3:8b")
        else:
            if req.task == "code":
                cascade.extend(["qwen2.5-coder:7b", "gemini-3.6-flash", "qwen3:8b"])
            elif req.task == "vision":
                cascade.extend(["gemma4e4b:latest", "gemini-3.6-flash"])
            else:
                cascade.extend(["qwen3:8b", "gemini-3.6-flash"])

        # Dédoublonnage en conservant l'ordre
        seen = set()
        ordered_cascade = []
        for model in cascade:
            if model in self.catalog and model not in seen:
                seen.add(model)
                ordered_cascade.append(model)

        return ordered_cascade
""",
    # 6. Provider Ollama
    "runtime/model_router/providers/ollama.py": r"""import requests
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
""",
    # 7. Provider Gemini
    "runtime/model_router/providers/gemini.py": r"""import os
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

        return ModelResponse(
            content=content,
            model_used=model,
            provider_used="gemini",
            latency_ms=latency
        )
""",
    # 8. Main Router Orchestrator
    "runtime/model_router/router.py": r"""import json
from pathlib import Path
from typing import Dict, Any, Optional

from .schemas import ModelRequest, ModelResponse
from .selector import ModelSelector
from .health import ModelHealthChecker
from .telemetry import RouterTelemetry
from .providers.ollama import OllamaProvider
from .providers.gemini import GeminiProvider

class EzzioModelRouter:
    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path) if config_path else Path(__file__).parent / "config.json"
        self.config = json.loads(cfg_file.read_text(encoding="utf-8"))

        self.catalog = self.config.get("catalog", {})
        self.selector = ModelSelector(self.catalog)
        self.health = ModelHealthChecker(self.config)
        self.telemetry = RouterTelemetry()

        self.ollama = OllamaProvider(self.config.get("ollama_host", "http://127.0.0.1:11434"))
        self.gemini = GeminiProvider()

    def generate(self, req: ModelRequest, agent_id: str = "system") -> ModelResponse:
        cascade = self.selector.select_cascade(req)
        last_error = None
        fallback_flag = False

        for idx, model_name in enumerate(cascade):
            if idx > 0:
                fallback_flag = True

            meta = self.catalog.get(model_name, {})
            provider_type = meta.get("provider")

            try:
                if provider_type == "ollama":
                    if not self.health.check_ollama():
                        continue
                    resp = self.ollama.execute(model_name, req, keep_alive=self.config.get("default_keep_alive", "5m"))
                elif provider_type == "gemini":
                    if not self.health.check_gemini():
                        continue
                    resp = self.gemini.execute(model_name, req)
                else:
                    continue

                resp.fallback_applied = fallback_flag
                self.telemetry.log_usage(agent_id, req.task, resp)
                return resp

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Échec de la cascade du Model Router. Dernier échec : {last_error}")
""",
    # 9. Package Init
    "runtime/model_router/__init__.py": """from .schemas import ModelRequest, ModelResponse
from .router import EzzioModelRouter

__all__ = ["ModelRequest", "ModelResponse", "EzzioModelRouter"]
""",
}

for rel_path, content in files.items():
    full_path = ROOT / Path(rel_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    print(f"[OK] Fichier déployé : {rel_path}")

print("\n[OK] Package runtime/model_router/ v1 déployé avec succès.")
