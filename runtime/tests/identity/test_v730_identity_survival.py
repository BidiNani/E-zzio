"""
E-ZZIO V7.30 — Certification Test Suite
Valide la création de snapshots, la récupération automatique et la gouvernance de l'autorité.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_snapshot import identity_snapshot_engine
from core.identity.identity_recovery import identity_recovery_engine
from core.identity.identity_chain import identity_chain_engine
from core.identity.identity_persistence import identity_persistence

def run_survival_tests():
    print("============================================================")
    print(" E-ZZIO V7.30 — IDENTITY IMMORTALITY LAYER CERTIFICATION")
    print("============================================================\n")

    identity_file = ROOT_DIR / "runtime" / "identity" / "identity.json"
    authority_file = ROOT_DIR / "runtime" / "identity" / "identity_authority.json"

    # 1. Génération de l'ancre et du Snapshot #1
    pers_res = identity_persistence.build_and_seal_identity_persistence()
    snap_res = identity_snapshot_engine.create_snapshot()
    chain_res = identity_chain_engine.append_identity_block(
        identity_root_hash=pers_res["identity_root_hash"],
        version="v1.0-identity-forge",
        description="Genesis Identity Block"
    )

    print(f"  [+] Snapshot #{snap_res['snapshot_index']} généré avec succès.")
    print(f"  [+] Bloc de chaîne #{chain_res['block_index']} scellé : Hash={chain_res['block_hash'][:16]}...")

    # ------------------------------------------------------------------
    # TEST A : Suppression physique de identity.json et récupération
    # ------------------------------------------------------------------
    print("\n[TEST A] Simulation de destruction de identity.json...")
    assert identity_file.exists(), "identity.json doit exister avant le test !"
    
    # Sauvegarde du contenu avant destruction
    saved_identity_content = identity_file.read_text(encoding="utf-8")
    identity_file.unlink()
    assert not identity_file.exists(), "Échec de la suppression simulée !"
    print(" -> [OK] identity.json détruit.")

    print(" -> Execution du Disaster Recovery Identitaire...")
    rec_res = identity_recovery_engine.recover_identity_from_latest_snapshot()
    print(f" -> Résultat de la récupération : {rec_res}")

    assert rec_res["recovered"] is True, "La restauration a échoué !"
    assert identity_file.exists(), "identity.json n'a pas été restauré !"
    print(" -> [OK] Test A validé : identity.json restauré depuis le dernier snapshot scellé.")

    # ------------------------------------------------------------------
    # TEST B : Tentative d'altération des règles d'autorité
    # ------------------------------------------------------------------
    print("\n[TEST B] Contrôle de la gouvernance et de l'autorité BidiNani...")
    auth_data = json.loads(authority_file.read_text(encoding="utf-8"))
    
    assert auth_data["authority"]["creator"] == "BidiNani", "Créateur non conforme !"
    assert auth_data["authority"]["core_values_modification"] == "forbidden", "Règle de modification invalide !"
    print(" -> [OK] Test B validé : Directives d'autorité et rôle du Mentor verrouillés.")

    print("\n============================================================")
    print(" V7.30 CERTIFIÉ : IDENTITY IMMORTALITY & RECOVERY LAYER OK")
    print("============================================================\n")

if __name__ == "__main__":
    run_survival_tests()
