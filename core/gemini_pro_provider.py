import os
from pathlib import Path
import sys

# Intégration du module d'optimisation et de compression de tokens[cite: 1]
sys.path.append(str(Path(__file__).resolve().parent.parent / "runtime" / "optimization"))
try:
    from token_compressor import compress_text, estimate_tokens
except ImportError:

    def compress_text(text, **kwargs):
        return {"compressed": text, "ratio": 1.0}

    def estimate_tokens(text):
        return len(text) // 4


try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None


class GeminiProProvider:
    """Connecteur souverain pour l'intégration de Gemini Pro dans le micro-noyau d'E-zzio."""

    def __init__(self, api_key: str = None):
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_key_from_env_file()

        if genai and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _load_key_from_env_file(self) -> str:
        r"""Charge la clé API depuis le fichier secrets\.env du projet."""
        # Recherche prioritaire dans secrets\.env à la racine
        env_paths = [Path(__file__).resolve().parent.parent / "secrets" / ".env", Path("G:/AI/E-zzio/secrets/.env"), Path("secrets/.env")]

        for path in env_paths:
            if path.exists():
                try:
                    for line in path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "GEMINI_API_KEY" in line:
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                return parts[1].strip().strip("\"'")
                except Exception:
                    pass
        return os.environ.get("GEMINI_API_KEY")

    def execute_advanced_reasoning(self, prompt: str, system_instruction: str = None, max_output_tokens: int = 8192) -> dict:
        raise PermissionError(
            "[FAIL-CLOSED] Accès direct GeminiPro interdit hors fédération : "
            "passer par CoderModelFederationRouter (CanonicalModelRegistry)."
        )
        if not self.client:
            return {
                "ok": False,
                "error": r"Client Gemini Pro non initialisé (clé introuvable dans secrets\.env ou variable d'environnement).",
            }

        try:
            optimization_result = compress_text(prompt, max_chars=16000, mode="extractive")

            config = types.GenerateContentConfig(
                system_instruction=system_instruction, max_output_tokens=max_output_tokens, temperature=0.7
            )

            response = self.client.models.generate_content(
                model="gemini-3.1-pro-preview", contents=optimization_result["compressed"], config=config
            )

            return {
                "ok": True,
                "response_text": response.text,
                "usage": getattr(response, "usage_metadata", None),
                "compression_ratio": optimization_result["ratio"],
            }
        except Exception as e:
            return {"ok": False, "error": f"Erreur d'exécution Gemini Pro : {str(e)}"}


# Instance prête pour le routage central
gemini_provider = GeminiProProvider()
