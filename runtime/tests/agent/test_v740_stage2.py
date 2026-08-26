"""
E-ZZIO V7.40-43 — Certification Test Suite (Agent Stage 2)
Valide la planification, la rédaction stylisée et la génération de code validée.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.agent.task_engine import task_engine
from core.agent.writing_engine import writing_engine
from core.agent.coding_assistant import coding_assistant


def run_agent_stage2_certification():
    print("============================================================")
    print(" E-ZZIO V7.40-V7.43 — AGENT LAYER STAGE 2 CERTIFICATION")
    print("============================================================\n")

    # [V7.40] Task Engine
    print(" [V7.40] AUTONOMOUS TASK ENGINE")
    plan = task_engine.create_execution_plan("Code un addon WoW pour le druide")
    assert "GENERATE_CODE" in plan["tasks"], "La planification n'a pas détecté la cible de code !"
    print(f"  -> Planification réussie. Étapes : {' -> '.join(plan['tasks'])}")
    print("  => V7.40 CERTIFIÉ\n")

    # [V7.42] Writing Engine
    print(" [V7.42] CREATIVE WRITING ENGINE")
    doc = writing_engine.generate_content("API Discord", "L'API utilise des websockets.")
    assert doc["fact_checked"] is True, "Le Fact-Check a échoué."
    assert "STYLE:" in doc["content"], "Le style Persona n'a pas été appliqué."
    print(f"  -> Style appliqué : {doc['style_applied']}")
    print("  => V7.42 CERTIFIÉ\n")

    # [V7.43] Coding Assistant Core
    print(" [V7.43] CODING ASSISTANT CORE")
    code_req = "Créer une fonction de somme"
    good_code = "def compute_sum(a, b):\n    return a + b"

    code_res = coding_assistant.generate_and_validate_code(code_req, good_code)
    assert code_res["quality_gate_passed"] is True, "Le code valide a été rejeté par la QG."
    print(f"  -> Génération validée par Quality Gate. Statut : {code_res['status']}")
    print("  => V7.43 CERTIFIÉ")

    print("\n============================================================")
    print(" STATUS : PRODUCTION ENGINES (CODE/WRITE/PLAN) ACTIVÉS")
    print("============================================================\n")


if __name__ == "__main__":
    run_agent_stage2_certification()
