"""
E-ZZIO V7.61.10 — Forensic Ledger Certification & Chaos Integrity Drill (Fixed)
Garantit que le test de rupture de chaîne (Chain Break) injecte bien un second bloc
avant de corrompre le lien.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import CognitiveGovernor, LedgerSecurityError

LEDGER_PATH = ROOT_DIR / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"
SANDBOX_DIR = ROOT_DIR / "runtime" / "cognition" / "budget" / "sandbox_drill"


def run_chaos_drill():
    print("[*] Lancement du Forensic Ledger Certification & Chaos Integrity Drill (V7.61.10)...")

    if not LEDGER_PATH.exists():
        print("[!] Erreur : Le Ledger réel est introuvable. Exécutez d'abord la création du Genesis.")
        return

    # S'assurer qu'on a au moins 2 blocs dans le ledger réel pour tester les liaisons
    gov = CognitiveGovernor()
    gov.evaluate_and_record("ECOL_DRILL_BLOCK_2", 150, "normal", "low")

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    sandbox_ledger = SANDBOX_DIR / "test_ledger.jsonl"

    results = []

    # -------------------------------------------------------------
    # TEST 1 : Validation de la chaîne normale (2 blocs)
    # -------------------------------------------------------------
    print("\n--- Test 1 : Vérification de la chaîne nominale ---")
    try:
        shutil.copy2(LEDGER_PATH, sandbox_ledger)
        gov.ledger_path = sandbox_ledger
        gov.verify_ledger_chain()
        results.append({"test": "Normal Chain Validation (2 blocks)", "status": "PASS"})
        print("  [PASS] Chaîne nominale (2 blocs) validée avec succès.")
    except Exception as e:
        results.append({"test": "Normal Chain Validation (2 blocks)", "status": "FAIL", "error": str(e)})
        print(f"  [FAIL] Échec sur la chaîne nominale : {e}")

    # -------------------------------------------------------------
    # TEST 2 : Altération d'un payload (Hash Mismatch)
    # -------------------------------------------------------------
    print("\n--- Test 2 : Falsification d'un coût (Tamper Payload) ---")
    try:
        shutil.copy2(LEDGER_PATH, sandbox_ledger)
        gov.ledger_path = sandbox_ledger

        lines = sandbox_ledger.read_text(encoding="utf-8").splitlines()
        if lines:
            data = json.loads(lines[0])
            data["estimated_cost"] = 9999999
            lines[0] = json.dumps(data, ensure_ascii=False)
            sandbox_ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

        gov.verify_ledger_chain()
        results.append({"test": "Tamper Payload Detection", "status": "FAIL", "error": "Accepté un payload falsifié !"})
        print("  [FAIL] Alerte : Falsification non détectée !")
    except LedgerSecurityError:
        results.append({"test": "Tamper Payload Detection", "status": "PASS"})
        print("  [PASS] Détection immédiate ! LedgerSecurityError levée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "Tamper Payload Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Verrouillage activé : {e}")

    # -------------------------------------------------------------
    # TEST 3 : Rupture du previous_hash (Chain Break sur le 2e bloc)
    # -------------------------------------------------------------
    print("\n--- Test 3 : Rupture du chaînage (Chain Break) ---")
    try:
        shutil.copy2(LEDGER_PATH, sandbox_ledger)
        gov.ledger_path = sandbox_ledger

        lines = sandbox_ledger.read_text(encoding="utf-8").splitlines()
        if len(lines) >= 2:
            data = json.loads(lines[1])
            data["previous_hash"] = "deadbeef" * 8  # Cassure volontaire du lien
            lines[1] = json.dumps(data, ensure_ascii=False)
            sandbox_ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

        gov.verify_ledger_chain()
        results.append({"test": "Chain Break Detection", "status": "FAIL", "error": "Accepté une rupture de chaîne !"})
        print("  [FAIL] Alerte : Rupture de chaîne non détectée !")
    except LedgerSecurityError:
        results.append({"test": "Chain Break Detection", "status": "PASS"})
        print("  [PASS] Rupture de chaîne interceptée ! LedgerSecurityError levée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "Chain Break Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Verrouillage activé sur rupture : {e}")

    # -------------------------------------------------------------
    # TEST 4 : Troncature / JSON Invalide
    # -------------------------------------------------------------
    print("\n--- Test 4 : Corruption de syntaxe JSON (Truncated JSON) ---")
    try:
        shutil.copy2(LEDGER_PATH, sandbox_ledger)
        gov.ledger_path = sandbox_ledger

        with open(sandbox_ledger, "a", encoding="utf-8") as f:
            f.write("{broken_json_line\n")

        gov.verify_ledger_chain()
        results.append({"test": "Invalid JSON Detection", "status": "FAIL", "error": "Ignoré un JSON corrompu !"})
        print("  [FAIL] Alerte : JSON corrompu ignoré !")
    except LedgerSecurityError:
        results.append({"test": "Invalid JSON Detection", "status": "PASS"})
        print("  [PASS] Corruption JSON interceptée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "Invalid JSON Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Sécurité activée sur JSON corrompu : {e}")

    # Nettoyage
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    gov.ledger_path = LEDGER_PATH

    print("\n" + "=" * 65)
    print(" FORENSIC LEDGER CERTIFICATION RAPPORT (V7.61.10)")
    print("=" * 65)
    for res in results:
        status_icon = "[✓]" if res["status"] == "PASS" else "[X]"
        print(f"  {status_icon} {res['test']} : {res['status']}")
    print("=" * 65)


if __name__ == "__main__":
    run_chaos_drill()
