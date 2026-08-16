"""
E-ZZIO V7.28.5.2 — Multi-Rotation & Merkle Chain Lineage Test
Valide que l'archive #2 pointe cryptographiquement vers la racine de l'archive #1.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from core.security.ledger_engine import LedgerEngine
from core.security.ledger_validator import ledger_validator

def run_multi_rotation_test():
    print("============================================================")
    print(" E-ZZIO V7.28.5.2 — CERTIFICATION DOUBLE ROTATION & LIGNAGE")
    print("============================================================\n")

    ledger_path = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
    archive_dir = ROOT_DIR / "runtime" / "decisions" / "archive"
    state_path = ROOT_DIR / "runtime" / "state" / "ledger_chain_state.json"

    # Nettoyage complet pour un test stérile
    if ledger_path.exists(): ledger_path.unlink()
    if state_path.exists(): state_path.unlink()
    for meta in archive_dir.glob("*.meta.json"): meta.unlink()
    for arc in archive_dir.glob("*.jsonl"): arc.unlink()

    # Seuil court de 50 transactions pour forcer les rotations rapidement
    engine = LedgerEngine(archive_threshold=50)

    print("[*] Injection de 125 transactions (déclenchera 2 rotations : à 50 et à 100)...")
    for i in range(125):
        success = engine.commit_transaction(
            intent="multi_archive_test",
            request_id=f"req-multi-{i}",
            candidates=[],
            selected="qwen3:8b",
            state="COMPLETED",
            execution_details={"index": i}
        )
        assert success is True, f"Échec de commit à l'itération {i}"

    # Récupération des archives et métadonnées triées par index
    archives = sorted(archive_dir.glob("ledger_*.jsonl"))
    metas = sorted(archive_dir.glob("ledger_*.meta.json"))

    print(f"  -> Nombre total d'archives générées : {len(archives)}")
    assert len(archives) == 2, f"Attendu exactement 2 archives, trouvé {len(archives)} !"
    assert len(metas) == 2, f"Attendu exactement 2 fichiers de métadonnées, trouvé {len(metas)} !"

    meta_1 = json.loads(metas[0].read_text(encoding="utf-8"))
    meta_2 = json.loads(metas[1].read_text(encoding="utf-8"))

    print(f"\n  [Archive #1] Séquences : {meta_1['first_sequence']} → {meta_1['last_sequence']}")
    print(f"               Root Hash : {meta_1['archive_root_hash']}")
    
    print(f"\n  [Archive #2] Séquences : {meta_2['first_sequence']} → {meta_2['last_sequence']}")
    print(f"               Prev Root : {meta_2['previous_archive_root_hash']}")
    print(f"               Root Hash : {meta_2['archive_root_hash']}")

    # VÉRIFICATION DU LIGNAGE CRYPTOGRAPHIQUE INTER-ARCHIVES
    assert meta_2["previous_archive_root_hash"] == meta_1["archive_root_hash"], (
        "RUPTURE DE CHAÎNE INTER-ARCHIVES : L'archive #2 ne pointe pas vers la racine de l'archive #1 !"
    )
    print("\n  [CERT] Lignage cryptographique inter-archives validé à 100% : Archive #2 scelle Archive #1.")

    # Validation du ledger actif résiduel (transactions 101 à 125 + les 2 ancres intermédiaires)
    active_val = ledger_validator.verify_ledger_chain()
    print(f"\n  -> Validation de la chaîne du ledger actif post-double rotation : {active_val}")
    assert active_val["valid"] is True, f"Le ledger actif a rompu la chaîne : {active_val.get('error')}"
    print(f"  -> Nombre total d'enregistrements actifs valides : {active_val['total_records']}")

    print("\n============================================================")
    print(" V7.28.5.2 CERTIFIÉ : MERKLE LINEAGE INTER-ARCHIVES VALIDÉ")
    print("============================================================\n")

if __name__ == "__main__":
    run_multi_rotation_test()
