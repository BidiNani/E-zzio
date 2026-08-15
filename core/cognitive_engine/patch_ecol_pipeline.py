"""
E-ZZIO V7.61.1 — ECOL Pipeline Patcher
Génère proprement les modules token_optimizer.py, prompt_compressor.py,
capability_selector.py et met à niveau model_router.py sans erreur de syntaxe.
"""
import os
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
CORE_COG_DIR = ROOT_DIR / "core" / "cognition"

NEW_MODULES = {
    "token_optimizer.py": ("TokenOptimizer", "Analyse, nettoie et déduplique l'input brut avant traitement."),
    "prompt_compressor.py": ("PromptCompressor", "Compresse la mémoire symbolique pour maximiser l'attention du LLM."),
    "capability_selector.py": ("CapabilitySelector", "Détermine si la tâche requiert un LLM, un script local ou une API cloud.")
}

MODEL_ROUTER_CODE = '''"""
E-ZZIO Core — Tactical Model Router (ECOL V7.61)
Sélectionne le moteur cognitif en fonction du vecteur de coût et de la capacité requise.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ModelRouter:
    def __init__(self):
        self.local_fast = "qwen2.5:3b"
        self.local_coder = "qwen2.5-coder:7b"
        self.cloud_complex = "claude-3-5-sonnet"

    def select_engine(self, task_type: str, complexity_score: float, risk_level: str) -> Dict[str, str]:
        """Aiguillage capacitaire strict."""
        if complexity_score < 0.3 and risk_level == "low":
            engine = self.local_fast
            provider = "ollama"
        elif "code" in task_type or "architecture" in task_type:
            engine = self.local_coder
            provider = "ollama"
        else:
            engine = self.cloud_complex
            provider = "api"
            
        logger.info(f"Routage cognitif -> Fournisseur: {provider} | Moteur: {engine}")
        return {"provider": provider, "model": engine}
'''

def apply_patch():
    print("[*] Application du correctif ECOL Pipeline V7.61.1...")
    CORE_COG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Création des nouveaux modules
    for filename, (class_name, description) in NEW_MODULES.items():
        filepath = CORE_COG_DIR / filename
        content = f'''"""
E-ZZIO Core — ECOL Pipeline
Module: {filename}
Description: {description}
"""
import logging

logger = logging.getLogger(__name__)

class {class_name}:
    def __init__(self):
        logger.debug("Initialisation du pipeline ECOL : %s", self.__class__.__name__)

    def process(self, payload: dict) -> dict:
        # Implémentation logique à relier à la Gateway
        return payload
'''
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"  + Module créé : {filename} (Classe: {class_name})")

    # 2. Mise à niveau du Model Router
    router_path = CORE_COG_DIR / "model_router.py"
    with open(router_path, "w", encoding="utf-8") as f:
        f.write(MODEL_ROUTER_CODE.strip() + "\n")
    print("  + Module mis à niveau : model_router.py (Aiguillage capacitaire)")

    print("\n" + "="*65)
    print(" ECOL PIPELINE PATCH (V7.61.1) APPLIQUE AVEC SUCCES")
    print("="*65)

if __name__ == "__main__":
    apply_patch()
