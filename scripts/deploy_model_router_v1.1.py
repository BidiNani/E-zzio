import json
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTER_DIR = ROOT / "runtime" / "model_router"
PROVIDERS_DIR = ROUTER_DIR / "providers"

# 1. Mise à jour de config.json avec prérequis RAM (GB)
config_data = {
    "ollama_host": "http://127.0.0.1:11434",
    "default_keep_alive": "5m",
    "catalog": {
        "qwen3:8b": {
            "provider": "ollama",
            "capabilities": ["chat", "general", "orchestration"],
            "max_complexity": "medium",
            "required_ram_gb": 6.0,
        },
        "qwen2.5-coder:7b": {
            "provider": "ollama",
            "capabilities": ["code", "scripting"],
            "max_complexity": "medium",
            "required_ram_gb": 5.0,
        },
        "gemma4e4b:latest": {"provider": "ollama", "capabilities": ["vision", "ocr"], "max_complexity": "low", "required_ram_gb": 5.5},
        "gemini-3.6-flash": {
            "provider": "gemini",
            "capabilities": ["chat", "code", "vision", "general"],
            "max_complexity": "high",
            "required_ram_gb": 0.0,
        },
        "gemini-2.5-pro": {
            "provider": "gemini",
            "capabilities": ["architecture", "reasoning", "complex_code"],
            "max_complexity": "critical",
            "required_ram_gb": 0.0,
        },
        "Qwen3-Coder-30B-A3B": {
            "provider": "llama_cpp",
            "capabilities": ["complex_code", "refactoring"],
            "model_path": "models/gguf/code/Qwen3-Coder-30B-A3B-Q4_K_M.gguf",
            "required_ram_gb": 18.0,
        },
        "DeepSeek-R1-Distill-Qwen-8B": {
            "provider": "llama_cpp",
            "capabilities": ["reasoning", "logic"],
            "model_path": "models/gguf/reasoning/DeepSeek-R1-Distill-Qwen-8B-Q4_K_M.gguf",
            "required_ram_gb": 7.0,
        },
    },
}
(ROUTER_DIR / "config.json").write_text(json.dumps(config_data, indent=2), encoding="utf-8")

# 2. Ajout du Provider GGUF (llama_cpp.py)
llama_cpp_code = """import os
import time
import subprocess
from pathlib import Path
from ..schemas import ModelRequest, ModelResponse

class LlamaCppProvider:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def execute(self, model_meta: dict, req: ModelRequest) -> ModelResponse:
        rel_path = model_meta.get("model_path", "")
        full_path = self.root_dir / rel_path

        if not full_path.exists():
            raise FileNotFoundError(f"Fichier GGUF introuvable : {full_path}")

        start_time = time.time()

        # Mode dégrade via CLI llama.cpp ou binding si installé
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=str(full_path), n_ctx=2048, verbose=False)
            output = llm(req.prompt, max_tokens=512)
            content = output["choices"][0]["text"]
        except ImportError:
            # Fallback execution CLI
            cmd = ["llama-cli", "-m", str(full_path), "-p", req.prompt, "-n", "512"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"Erreur d'exécution llama-cli: {result.stderr}")
            content = result.stdout.strip()

        latency = (time.time() - start_time) * 1000

        return ModelResponse(
            content=content,
            model_used=model_meta.get("model_path", "gguf"),
            provider_used="llama_cpp",
            latency_ms=latency
        )
"""
(PROVIDERS_DIR / "llama_cpp.py").write_text(llama_cpp_code, encoding="utf-8")

# 3. Guard RAM & Governor Health (health.py)
health_code = """import requests
import os
import psutil
from pathlib import Path
from typing import Dict, Any

class ModelHealthChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_host = config.get("ollama_host", "http://127.0.0.1:11434")

    def check_ollama(self) -> bool:
        try:
            res = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def check_gemini(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def check_ram_availability(self, required_ram_gb: float) -> bool:
        if required_ram_gb <= 0:
            return True
        free_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        return free_ram_gb >= required_ram_gb
"""
(ROUTER_DIR / "health.py").write_text(health_code, encoding="utf-8")

# 4. Orchestrateur Router Mis à jour avec Controle RAM
router_code = """import json
from pathlib import Path
from typing import Dict, Any, Optional

from .schemas import ModelRequest, ModelResponse
from .selector import ModelSelector
from .health import ModelHealthChecker
from .telemetry import RouterTelemetry
from .providers.ollama import OllamaProvider
from .providers.gemini import GeminiProvider
from .providers.llama_cpp import LlamaCppProvider

class EzzioModelRouter:
    def __init__(self, config_path: Optional[str] = None):
        self.root_dir = Path(r"G:\\AI\\E-zzio")
        cfg_file = Path(config_path) if config_path else Path(__file__).parent / "config.json"
        self.config = json.loads(cfg_file.read_text(encoding="utf-8"))

        self.catalog = self.config.get("catalog", {})
        self.selector = ModelSelector(self.catalog)
        self.health = ModelHealthChecker(self.config)
        self.telemetry = RouterTelemetry()

        self.ollama = OllamaProvider(self.config.get("ollama_host", "http://127.0.0.1:11434"))
        self.gemini = GeminiProvider()
        self.llama_cpp = LlamaCppProvider(self.root_dir)

    def generate(self, req: ModelRequest, agent_id: str = "system") -> ModelResponse:
        cascade = self.selector.select_cascade(req)
        last_error = None
        fallback_flag = False

        for idx, model_name in enumerate(cascade):
            if idx > 0:
                fallback_flag = True

            meta = self.catalog.get(model_name, {})
            provider_type = meta.get("provider")
            required_ram = meta.get("required_ram_gb", 0.0)

            # Vérification de sécurité RAM via Governor Guard
            if not self.health.check_ram_availability(required_ram):
                continue

            try:
                if provider_type == "ollama":
                    if not self.health.check_ollama():
                        continue
                    resp = self.ollama.execute(model_name, req, keep_alive=self.config.get("default_keep_alive", "5m"))
                elif provider_type == "gemini":
                    if not self.health.check_gemini():
                        continue
                    resp = self.gemini.execute(model_name, req)
                elif provider_type == "llama_cpp":
                    resp = self.llama_cpp.execute(meta, req)
                else:
                    continue

                resp.fallback_applied = fallback_flag
                self.telemetry.log_usage(agent_id, req.task, resp)
                return resp

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Échec de la cascade du Model Router. Dernier échec : {last_error}")
"""
(ROUTER_DIR / "router.py").write_text(router_code, encoding="utf-8")

print("[OK] Model Router v1.1 (Intégré Kernel + Guard RAM + Provider GGUF) déployé.")
