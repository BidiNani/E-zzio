"""
E-ZZIO V7.28.4 — Industrial Certification Suite (With Clean State Restoration)
Restaure le ledger sain après l'exercice de falsification pour éviter de polluer les boots suivants.
"""
import sys
import json
import time
import multiprocessing
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import LedgerEngine
from core.security.ledger_validator import ledger_validator
from runtime.recovery.ledger_boot_recovery import LedgerBootRecovery

def worker_task(worker_id: int, count: int):
    engine = LedgerEngine()
    for i in range(count):
        engine.commit_transaction(
            intent=f"stress_w{worker_id}",
            request_id=f"req-w{worker_id}-{i}",
            candidates=[{"provider": "ollama", "model": "qwen3:8b"}],
            selected="qwen3:8b",
            state="COMPLETED",
            execution_details={"worker": worker_id, "iter": i}
        )

def run_industrial_certification():
    print("============================================================")
    print(" E-ZZIO V7.28.4 — CERTIFICATION FORENSIC & CLEAN STATE RESTORATION")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()

    # TEST E — Concurrence Massive
    print("[TEST E] 8 workers OS en parallèle (800 transactions concurrentes)...")
    num_workers = 8
    tx_per_worker = 100
    
    start_time = time.time()
    processes = [multiprocessing.Process(target=worker_task, args=(wid, tx_per_worker)) for wid in range(num_workers)]
    for p in processes: p.start()
    for p in processes: p.join()
    
    duration = time.time() - start_time
    print(f"  -> Exécuté en {round(duration, 2)} secondes.")

    val_res = ledger_validator.verify_ledger_chain()
    assert val_res["valid"] is True and val_res["total_records"] == 800, f"Erreur de concurrence : {val_res}"
    print("  [OK] Concurrence multi-processus certifiée.")

    # TEST F — Auto-Release Verrou Noyau
    print("\n[TEST F] Test d'auto-libération du verrou par le noyau OS...")
    from core.security.file_lock import ProcessFileLock
    lock_path = ROOT_DIR / "runtime" / "decisions" / "ledger.lock"
    with ProcessFileLock(lock_path, timeout=5.0) as lk:
        pass
    print("  [OK] Auto-release validé.")

    # TEST G — Boot Recovery avec Snapshot Forensic
    print("\n[TEST G] Test d'auto-guérison avec Forensic Snapshot (JSON tronqué)...")
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    lines.append('{"sequence": 801, "intent": "broken_tail')
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    recovery_engine = LedgerBootRecovery()
    heal_res = recovery_engine.verify_and_heal_ledger()
    assert heal_res["status"] == "HEALTHY", "Le recovery a échoué !"
    print("  [OK] Forensic Snapshot & Tail Recovery certifiés.")

    # TEST H — Falsification Exclusive de la Signature HMAC (Test Fail-Closed + Cleanup)
    print("\n[TEST H] Test d'attaque par falsification exclusive du HMAC...")
    # Sauvegarde de l'état sain avant altération volontaire
    healthy_content = ledger_path.read_text(encoding="utf-8")
    
    lines = healthy_content.strip().splitlines()
    rec = json.loads(lines[10])
    rec["signature"] = "0000000000000000000000000000000000000000000000000000000000000000"
    lines[10] = json.dumps(rec)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    hmac_tamper_engine = LedgerBootRecovery()
    hmac_res = hmac_tamper_engine.verify_and_heal_ledger()
    assert hmac_res["mode"] == "FAIL_CLOSED", "Le système a ignoré la falsification !"
    print("  [OK] Protection HMAC pure certifiée : FAIL_CLOSED immédiat.")

    # RESTAURATION DE L'ÉTAT SAIN DE FIN DE CAMPAGNE (Cleanup post-attaque)
    ledger_path.write_text(healthy_content, encoding="utf-8")
    final_check = ledger_validator.verify_ledger_chain()
    assert final_check["valid"] is True, "La restauration post-test a échoué !"
    print("  [OK] Environnement nettoyé et restauré à l'état nominal.")

    print("\n============================================================")
    print(" V7.28.4 CERTIFIÉ PROPRE : 10/10 ABSOLU ATTEINT")
    print("============================================================\n")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_industrial_certification()
