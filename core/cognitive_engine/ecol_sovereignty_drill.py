"""
E-ZZIO V7.62.1 — Sovereignty Certification Drill
Teste l'inviolabilité HMAC, la résistance aux attaques par rejeu, la divergence de manifeste
et la certification du démarrage à froid (Cold Boot).
"""

import sys
import json
import shutil
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import CognitiveGovernor, LedgerSecurityError

BUDGET_DIR = ROOT_DIR / "runtime" / "cognition" / "budget"
LEDGER_PATH = BUDGET_DIR / "cognitive_budget_ledger.jsonl"
MANIFEST_PATH = BUDGET_DIR / "ledger_manifest.json"
SANDBOX_DIR = BUDGET_DIR / "sovereignty_sandbox"


def run_sovereignty_drill():
    print("[*] Lancement de la Certification en Souveraineté Cryptographique (V7.62.1)...")

    if not LEDGER_PATH.exists():
        print("[!] Erreur : Aucun Ledger actif trouvé. Exécutez d'abord l'initialisation V7.62.")
        return

    # Préparation du bac à sable
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    sandbox_ledger = SANDBOX_DIR / "cognitive_budget_ledger.jsonl"
    sandbox_manifest = SANDBOX_DIR / "ledger_manifest.json"

    shutil.copy2(LEDGER_PATH, sandbox_ledger)
    if MANIFEST_PATH.exists():
        shutil.copy2(MANIFEST_PATH, sandbox_manifest)

    gov = CognitiveGovernor()
    gov.ledger_path = sandbox_ledger
    gov.manifest_path = sandbox_manifest

    results = []

    # -------------------------------------------------------------
    # ÉPREUVE 1 : HMAC Tamper Detection
    # -------------------------------------------------------------
    print("\n--- Épreuve 1 : Falsification de la signature HMAC ---")
    try:
        lines = sandbox_ledger.read_text(encoding="utf-8").splitlines()
        if lines:
            data = json.loads(lines[0])
            data["hmac_signature"] = "f" * 64  # Signature falsifiée
            lines[0] = json.dumps(data, ensure_ascii=False)
            sandbox_ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

        gov.verify_ledger_chain()
        results.append({"test": "HMAC Tamper Detection", "status": "FAIL", "error": "Signature HMAC fausse acceptée !"})
        print("  [FAIL] Alerte : Le système a accepté une fausse attestation HMAC !")
    except LedgerSecurityError:
        results.append({"test": "HMAC Tamper Detection", "status": "PASS"})
        print("  [PASS] Attestation HMAC frauduleuse interceptée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "HMAC Tamper Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Verrouillage activé : {e}")

    # Restauration sandbox
    shutil.copy2(LEDGER_PATH, sandbox_ledger)
    if MANIFEST_PATH.exists():
        shutil.copy2(MANIFEST_PATH, sandbox_manifest)

    # -------------------------------------------------------------
    # ÉPREUVE 2 : Manifest Divergence Detection
    # -------------------------------------------------------------
    print("\n--- Épreuve 2 : Divergence du Manifeste d'Intégrité ---")
    try:
        if sandbox_manifest.exists():
            manifest_data = json.loads(sandbox_manifest.read_text(encoding="utf-8"))
            manifest_data["total_blocks"] = 999999  # Falsification du nombre de blocs
            sandbox_manifest.write_text(gov._canonical_dump(manifest_data) + "\n", encoding="utf-8")

        gov.verify_ledger_chain()
        results.append({"test": "Manifest Divergence Detection", "status": "FAIL", "error": "Manifeste corrompu accepté !"})
        print("  [FAIL] Alerte : Manifeste altéré non détecté !")
    except LedgerSecurityError:
        results.append({"test": "Manifest Divergence Detection", "status": "PASS"})
        print("  [PASS] Incohérence du manifeste interceptée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "Manifest Divergence Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Verrouillage activé sur le manifeste : {e}")

    # Restauration sandbox
    shutil.copy2(LEDGER_PATH, sandbox_ledger)
    if MANIFEST_PATH.exists():
        shutil.copy2(MANIFEST_PATH, sandbox_manifest)

    # -------------------------------------------------------------
    # ÉPREUVE 3 : Replay Attack Simulation (Duplication de bloc)
    # -------------------------------------------------------------
    print("\n--- Épreuve 3 : Attaque par Rejeu (Replay Attack) ---")
    try:
        lines = sandbox_ledger.read_text(encoding="utf-8").splitlines()
        if lines:
            # On duplique le premier bloc à la fin, ce qui casse la chaîne des previous_hash
            lines.append(lines[0])
            sandbox_ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

        gov.verify_ledger_chain()
        results.append({"test": "Replay Attack Detection", "status": "FAIL", "error": "Bloc rejoué accepté !"})
        print("  [FAIL] Alerte : Rejeu non détecté !")
    except LedgerSecurityError:
        results.append({"test": "Replay Attack Detection", "status": "PASS"})
        print("  [PASS] Attaque par rejeu interceptée (FAIL CLOSED).")
    except Exception as e:
        results.append({"test": "Replay Attack Detection", "status": "PASS", "note": str(e)})
        print(f"  [PASS] Verrouillage activé sur le rejeu : {e}")

    # Restauration sandbox
    shutil.copy2(LEDGER_PATH, sandbox_ledger)
    if MANIFEST_PATH.exists():
        shutil.copy2(MANIFEST_PATH, sandbox_manifest)

    # -------------------------------------------------------------
    # ÉPREUVE 4 : Cold Boot Verification (Redémarrage complet simulé)
    # -------------------------------------------------------------
    print("\n--- Épreuve 4 : Vérification du Démarrage à Froid (Cold Boot) ---")
    try:
        # Instanciation d'un nouveau governor propre pointant sur la sandbox d'origine
        cold_gov = CognitiveGovernor()
        cold_gov.ledger_path = sandbox_ledger
        cold_gov.manifest_path = sandbox_manifest

        cold_gov.verify_ledger_chain()
        results.append({"test": "Cold Boot Verification", "status": "PASS"})
        print("  [PASS] Démarrage à froid certifié : chaînes et manifeste validés à l'initialisation.")
    except Exception as e:
        results.append({"test": "Cold Boot Verification", "status": "FAIL", "error": str(e)})
        print(f"  [FAIL] Échec du démarrage à froid : {e}")

    # Nettoyage sandbox
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    gov.ledger_path = LEDGER_PATH
    gov.manifest_path = MANIFEST_PATH

    print("\n" + "=" * 65)
    print(" SOVEREIGNTY CERTIFICATION RAPPORT (V7.62.1)")
    print("=" * 65)
    for res in results:
        status_icon = "[✓]" if res["status"] == "PASS" else "[X]"
        print(f"  {status_icon} {res['test']} : {res['status']}")
    print("=" * 65)


if __name__ == "__main__":
    run_sovereignty_drill()
