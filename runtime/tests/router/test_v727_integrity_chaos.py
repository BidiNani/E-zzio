"""
E-ZZIO V7.27 — Integrity & Chaos Certification Suite
Exécute un stress test de 1,000 transactions et simule 4 types d'attaques/altérations.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import ledger_engine
from core.security.ledger_validator import ledger_validator


def run_integrity_chaos():
    print("============================================================")
    print(" E-ZZIO V7.27 — CAMPAGNE DE CHAOS & INTÉGRITÉ TRANSACTIONNELLE")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()  # Reset pour le test propre

    # TEST A — 1000 Transactions en écriture atomique
    print("[TEST A] Injection et validation de 1,000 transactions consécutives...")
    for i in range(1000):
        success = ledger_engine.commit_transaction(
            intent="stress_test",
            request_id=f"req-uuid-{i}",
            candidates=[{"provider": "ollama", "model": "qwen3:8b", "score": 0.9}],
            selected="qwen3:8b",
            state="COMPLETED",
            execution_details={"index": i},
        )
        assert success is True, f"Échec de commit à l'itération {i}"

    val_res = ledger_validator.verify_ledger_chain()
    print(f"  -> Résultat validation 1,000 tx : {val_res}")
    assert val_res["valid"] is True and val_res["total_records"] == 1000, "Le stress test a corrompu la chaîne !"
    print("  [OK] 1,000 transactions validées sans aucune erreur.")

    # Chargement des lignes pour les tests d'attaque
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()

    # TEST B — Corruption Volontaire (Modification du champ selected)
    print("\n[TEST B] Simulation d'une altération de données (Hash Tampering)...")
    rec = json.loads(lines[10])
    rec["selected"] = "modele_malveillant_injecte"
    lines_b = list(lines)
    lines_b[10] = json.dumps(rec)

    test_b_path = ROOT_DIR / "runtime" / "decisions" / "test_b.jsonl"
    test_b_path.write_text("\n".join(lines_b) + "\n", encoding="utf-8")

    import core.security.ledger_validator as lv

    orig_path = lv.LEDGER_PATH
    lv.LEDGER_PATH = test_b_path
    res_b = ledger_validator.verify_ledger_chain()
    lv.LEDGER_PATH = orig_path
    test_b_path.unlink()

    print(f"  -> Résultat de détection d'altération : {res_b}")
    assert res_b["valid"] is False and "HASH INVALID" in res_b["error"], "Le validateur n'a pas vu la modification !"
    print("  [OK] Altération de payload interceptée avec succès.")

    # TEST C — Suppression de Bloc (Rupture de Séquence)
    print("\n[TEST C] Simulation d'une suppression de ligne (Sequence Gap)...")
    lines_c = list(lines)
    lines_c.pop(50)  # Supprime la ligne 51 (séquence 51)

    test_c_path = ROOT_DIR / "runtime" / "decisions" / "test_c.jsonl"
    test_c_path.write_text("\n".join(lines_c) + "\n", encoding="utf-8")

    lv.LEDGER_PATH = test_c_path
    res_c = ledger_validator.verify_ledger_chain()
    lv.LEDGER_PATH = orig_path
    test_c_path.unlink()

    print(f"  -> Résultat de détection de rupture de séquence : {res_c}")
    assert res_c["valid"] is False and "SEQUENCE GAP DETECTED" in res_c["error"], "Le validateur n'a pas vu le saut de séquence !"
    print("  [OK] Rupture de séquence détectée avec succès.")

    # TEST D — Simulation de Crash (Ligne JSON tronquée)
    print("\n[TEST D] Simulation d'un crash kernel/panic pendant l'écriture (JSON Tronqué)...")
    lines_d = list(lines)
    lines_d.append('{"sequence": 1001, "timestamp": "2026-08-11", "intent": "partial_w')  # JSON cassé

    test_d_path = ROOT_DIR / "runtime" / "decisions" / "test_d.jsonl"
    test_d_path.write_text("\n".join(lines_d) + "\n", encoding="utf-8")

    lv.LEDGER_PATH = test_d_path
    res_d = ledger_validator.verify_ledger_chain()
    lv.LEDGER_PATH = orig_path
    test_d_path.unlink()

    print(f"  -> Résultat de détection de corruption d'atomicité : {res_d}")
    assert res_d["valid"] is False and "RECOVERABLE_CORRUPTION" in res_d["error"], "Le validateur n'a pas intercepté le JSON tronqué !"
    print("  [OK] Corruption atomique (crash d'écriture) isolée et identifiable.")

    print("\n============================================================")
    print(" V7.27 CERTIFIÉ : TRANSACTION INTEGRITY LAYER 10/10 ATTEINT")
    print("============================================================\n")


if __name__ == "__main__":
    run_integrity_chaos()
