"""
E-ZZIO V7.33 — Certification Test Suite (Quality Gate)
Valide l'autonomie d'évaluation et de filtrage d'E-ZZIO.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.quality_gate.quality_gate import quality_gate


def run_quality_gate_certification():
    print("============================================================")
    print(" E-ZZIO V7.33 — QUALITY GATE CERTIFICATION")
    print("============================================================\n")

    # [1/3] Candidat sain
    clean_code = "def compute_sum(a, b):\n    return a + b"
    res_clean = quality_gate.evaluate_candidate("clean_module.py", clean_code)
    assert res_clean["approved"] is True, "Le code propre a été rejeté !"
    print(" [1/3] Validation code sain : OK")

    # [2/3] Candidat avec faille de sécurité (eval)
    unsafe_code = "def evaluate_string(expr):\n    return eval(expr)"
    res_unsafe = quality_gate.evaluate_candidate("unsafe_module.py", unsafe_code)
    assert res_unsafe["approved"] is False, "Le code dangereux n'a pas été intercepté !"
    assert res_unsafe["stage"] == "security_scan", "Étage d'interception incorrect !"
    print(" [2/3] Interception code non sécurisé : OK")

    # [3/3] Candidat avec erreur de syntaxe
    syntax_error_code = "def broken_syntax(\n    pass"
    res_syntax = quality_gate.evaluate_candidate("broken_module.py", syntax_error_code)
    assert res_syntax["approved"] is False, "L'erreur de syntaxe n'a pas été détectée !"
    assert res_syntax["stage"] == "static_analyzer", "Étage d'interception syntaxique incorrect !"
    print(" [3/3] Interception erreur de syntaxe : OK")

    print("\n============================================================")
    print(" V7.33 CERTIFIÉ : AUTONOMOUS QUALITY GATE OPÉRATIONNEL")
    print("============================================================\n")


if __name__ == "__main__":
    run_quality_gate_certification()
