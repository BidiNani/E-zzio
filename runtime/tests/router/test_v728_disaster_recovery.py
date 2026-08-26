"""
E-ZZIO V7.28.7 — Disaster Recovery Certification Test
Simule la destruction totale du ledger actif et vérifie la reconstruction
transparente de l'état système à partir des archives scellées.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import LedgerEngine
from core.security.disaster_recovery import disaster_recovery


def run_disaster_test():
    print("============================================================")
    print(" E-ZZIO V7.28.7 — TEST DE RECONSTRUCTION APRÈS SINISTRE")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    archive_dir = ROOT_DIR / "runtime" / "decisions" / "archive"
    state_path = ROOT_DIR / "runtime" / "state" / "ledger_chain_state.json"

    # Nettoyage initial
    if ledger_path.exists():
        ledger_path.unlink()
    if state_path.exists():
        state_path.unlink()
    for meta in archive_dir.glob("*.meta.json"):
        meta.unlink()
    for arc in archive_dir.glob("*.jsonl"):
        arc.unlink()

    # Génération d'une archive via 60 transactions (seuil à 50)
    engine = LedgerEngine(archive_threshold=50)
    print("[*] Injection de 60 transactions (créera 1 archive de 50 txs et 10 txs actives)...")
    for i in range(60):
        engine.commit_transaction(
            intent="disaster_test",
            request_id=f"req-d-{i}",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED",
            execution_details={"index": i},
        )

    # Vérification de l'état avant sinistre
    archives_before = list(archive_dir.glob("ledger_*.jsonl"))
    assert len(archives_before) == 1, "L'archive n'a pas été générée !"

    meta_before = json.loads(list(archive_dir.glob("ledger_*.meta.json"))[0].read_text(encoding="utf-8"))
    expected_last_seq_in_archive = meta_before["last_sequence"]  # Devrait être 50
    expected_root_hash = meta_before["archive_root_hash"]

    print(f"  -> État nominal avant sinistre : Archive #1 scellée jusqu'à la séquence {expected_last_seq_in_archive}.")

    # ==========================================================
    # SIMULATION DU SINISTRE CATASTROPHIQUE
    # ==========================================================
    print("\n[!] CATASTROPHE SIMULÉE : Destruction totale et définitive du ledger actif et de l'état global...")
    if ledger_path.exists():
        ledger_path.unlink()  # Suppression pure et simple du fichier journal
    if state_path.exists():
        state_path.unlink()  # Suppression de l'ancre d'état

    assert not ledger_path.exists(), "Le ledger actif n'a pas pu être détruit pour le test !"
    print("  [OK] Le fichier de ledger actif est maintenant totalement oblitéré.")

    # LANCEMENT DE LA RÉCUPÉRATION APRÈS SINISTRE
    print("\n[*] Exécution du Disaster Recovery Engine...")
    recovery_result = disaster_recovery.reconstruct_state_from_archives()
    print(f"  -> Résultat de la reconstruction : {json.dumps(recovery_result, indent=2)}")

    assert recovery_result["recovered"] is True, f"La récupération a échoué : {recovery_result.get('error')}"
    assert recovery_result["last_sequence"] == expected_last_seq_in_archive, (
        "La séquence restaurée ne correspond pas à la dernière archive !"
    )
    assert recovery_result["root_hash"] == expected_root_hash, "Le Root Hash restauré est corrompu !"

    # Vérification que l'ancre d'état a bien été recréée sur le disque
    assert state_path.exists(), "L'ancre d'état n'a pas été recréée sur le disque !"
    restored_state = json.loads(state_path.read_text(encoding="utf-8"))
    print(f"  -> Ancre d'état restaurée sur disque : {restored_state}")

    print("\n============================================================")
    print(" V7.28.7 CERTIFIÉ : DISASTER RECOVERY & STATE RECONSTRUCTION OK")
    print("============================================================\n")


if __name__ == "__main__":
    run_disaster_test()
