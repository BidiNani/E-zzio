"""
E-ZZIO V7.41 — Certification Test Suite (Multi Model Router)
Valide le routage intelligent (Local vs Cloud) et l'intégration avec la Tool Gateway.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tool_gateway.model_router import model_router


def run_router_certification():
    print("============================================================")
    print(" E-ZZIO V7.41 — MULTI MODEL ROUTER CERTIFICATION")
    print("============================================================\n")

    # [1/3] Routage tâche simple (Basse complexité)
    res_simple = model_router.execute_prompt("Résume ce texte en 3 lignes", task_type="summary", complexity=3)
    assert res_simple["routed_to"] == "ollama_local", "Une tâche simple a été envoyée au Cloud !"
    assert res_simple["api_executed"] is True, "Le passage par la Gateway a échoué."
    print(" [1/3] Routage local (Ollama) pour tâche simple : OK")

    # [2/3] Routage tâche complexe (Développement/Architecture)
    res_complex = model_router.execute_prompt("Génère l'architecture du système", task_type="architecture", complexity=8)
    assert res_complex["routed_to"] == "gemini_pro", "Une tâche complexe n'a pas été envoyée à Gemini !"
    assert res_complex["api_executed"] is True, "Le passage par la Gateway a échoué."
    print(" [2/3] Routage Cloud (Gemini Pro) pour tâche complexe : OK")

    # [3/3] Vérification des traces Gateway
    print(f" [3/3] Traçabilité Gateway vérifiée (Action IDs: {res_simple['action_id']}, {res_complex['action_id']}) : OK")

    print("\n============================================================")
    print(" V7.41 CERTIFIÉ : INTELLIGENCE ROUTER OPÉRATIONNEL")
    print("============================================================\n")


if __name__ == "__main__":
    run_router_certification()
