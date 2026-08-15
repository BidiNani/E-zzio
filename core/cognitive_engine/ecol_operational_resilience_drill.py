"""
E-ZZIO V7.61.11 — Operational Resilience Drill
Valide la crash-consistency (ligne partielle), la concurrence multi-thread (RLock stress),
et le drill de restauration/reprise après sinistre.
"""
import os
import sys
import json
import threading
import shutil
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import CognitiveGovernor, LedgerSecurityError

LEDGER_PATH = ROOT_DIR / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"
BACKUP_PATH = LEDGER_PATH.with_suffix(".jsonl.pre-industrial.bak")

def run_resilience_drill():
    print("[*] Lancement de l'Operational Resilience Drill (V7.61.11)...")
    governor = CognitiveGovernor()
    results = []

    # -------------------------------------------------------------
    # TEST 1 : Crash-Consistency (Ligne finale tronquée / partielle)
    # -------------------------------------------------------------
    print("\n--- Test 1 : Crash Consistency (Interruption d'écriture) ---")
    try:
        # On sauvegarde l'état actuel
        temp_backup = LEDGER_PATH.with_suffix(".jsonl.temp_drill")
        shutil.copy2(LEDGER_PATH, temp_backup)

        # Injection d'une ligne tronquée simulant un crash d'écriture au milieu d'un commit
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write('{"runtime_id": "EZZIO-RUNTIME-001", "task": "CRASHED_WRI')
            f.flush()

        # Tentative d'instanciation ou de vérification : doit lever un Fail-Closed
        try:
            broken_gov = CognitiveGovernor()
            results.append({"test": "Crash Consistency (Truncated Line)", "status": "FAIL", "error": "Le système a ignoré une ligne partielle !"})
            print("  [FAIL] Alerte : Ligne partielle ignorée sans erreur !")
        except LedgerSecurityError:
            results.append({"test": "Crash Consistency (Truncated Line)", "status": "PASS"})
            print("  [PASS] Crash détecté ! Interception immédiate (FAIL CLOSED).")

        # Restauration propre
        shutil.copy2(temp_backup, LEDGER_PATH)
        if temp_backup.exists():
            temp_backup.unlink()

    except Exception as e:
        results.append({"test": "Crash Consistency (Truncated Line)", "status": "FAIL", "error": str(e)})
        print(f"  [FAIL] Erreur inattendue : {e}")

    # -------------------------------------------------------------
    # TEST 2 : Concurrency Stress Test (Multi-Thread Multi-Write)
    # -------------------------------------------------------------
    print("\n--- Test 2 : Concurrency Stress Test (Écritures simultanées) ---")
    try:
        thread_count = 10
        writes_per_thread = 5
        errors = []

        def worker(thread_id):
            try:
                # Chaque thread instancie son governor ou partage l'instance sécurisée par RLock
                gov_local = CognitiveGovernor()
                for i in range(writes_per_thread):
                    gov_local.evaluate_and_record(f"THREAD_{thread_id}_TASK_{i}", 50, "normal", "low")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Vérification finale de l'intégrité globale de la chaîne après le stress test
        final_gov = CognitiveGovernor()
        final_gov.verify_ledger_chain()

        if not errors:
            results.append({"test": "Concurrency Stress Test", "status": "PASS"})
            print(f"  [PASS] {thread_count * writes_per_thread} écritures concurrentes exécutées sans collision. Chaîne intègre.")
        else:
            results.append({"test": "Concurrency Stress Test", "status": "FAIL", "error": str(errors)})
            print(f"  [FAIL] Erreurs concurrentes détectées : {errors}")

    except Exception as e:
        results.append({"test": "Concurrency Stress Test", "status": "FAIL", "error": str(e)})
        print(f"  [FAIL] Échec du test de concurrence : {e}")

    # -------------------------------------------------------------
    # TEST 3 : Recovery Drill (Restauration sur incident majeur)
    # -------------------------------------------------------------
    print("\n--- Test 3 : Recovery & Backup Drill (Reprise après sinistre) ---")
    try:
        # Simulation d'une destruction du Ledger actif
        disaster_backup = LEDGER_PATH.with_suffix(".jsonl.disaster_backup")
        shutil.copy2(LEDGER_PATH, disaster_backup)

        # Destruction
        LEDGER_PATH.unlink()
        print("  * Sinistre simulé : Ledger actif supprimé.")

        # Restauration depuis le backup de secours
        shutil.copy2(disaster_backup, LEDGER_PATH)
        if disaster_backup.exists():
            disaster_backup.unlink()

        # Reprise et vérification
        recovery_gov = CognitiveGovernor()
        recovery_gov.verify_ledger_chain()
        
        results.append({"test": "Disaster Recovery & Resume", "status": "PASS"})
        print("  [PASS] Restauration du Ledger réussie et reprise de l'activité validée.")

    except Exception as e:
        results.append({"test": "Disaster Recovery & Resume", "status": "FAIL", "error": str(e)})
        print(f"  [FAIL] Échec de la récupération : {e}")

    print("\n" + "=" * 65)
    print(" OPERATIONAL RESILIENCE CERTIFICATION RAPPORT (V7.61.11)")
    print("=" * 65)
    for res in results:
        status_icon = "[✓]" if res["status"] == "PASS" else "[X]"
        print(f"  {status_icon} {res['test']} : {res['status']}")
    print("=" * 65)

if __name__ == "__main__":
    run_resilience_drill()
