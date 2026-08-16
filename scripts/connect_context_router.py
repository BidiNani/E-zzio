import json
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTER_DIR = ROOT / "runtime" / "model_router"

router_code = """import json
from pathlib import Path
from typing import Dict, Any, Optional

from .schemas import ModelRequest, ModelResponse
from .selector import ModelSelector
from .health import ModelHealthChecker
from .telemetry import RouterTelemetry
from .context import EzzioContextInjector
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
        self.context_injector = EzzioContextInjector(self.root_dir)

        self.ollama = OllamaProvider(self.config.get("ollama_host", "http://127.0.0.1:11434"))
        self.gemini = GeminiProvider()
        self.llama_cpp = LlamaCppProvider(self.root_dir)

    def generate(self, req: ModelRequest, agent_id: str = "system") -> ModelResponse:
        # Injection automatique de l'identité et de l'état système E-ZZIO
        req.system_prompt = self.context_injector.build_system_prompt(req.system_prompt)

        cascade = self.selector.select_cascade(req)
        last_error = None
        fallback_flag = False

        for idx, model_name in enumerate(cascade):
            if idx > 0:
                fallback_flag = True

            meta = self.catalog.get(model_name, {})
            provider_type = meta.get("provider")
            required_ram = meta.get("required_ram_gb", 0.0)

            # Verification de la disponibilité RAM
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
print("[OK] Integration de EzzioContextInjector dans router.py terminée.")
