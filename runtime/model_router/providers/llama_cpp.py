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
            content=content, model_used=model_meta.get("model_path", "gguf"), provider_used="llama_cpp", latency_ms=latency
        )
