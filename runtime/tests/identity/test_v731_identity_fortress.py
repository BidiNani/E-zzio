"""
E-ZZIO V7.31 — Identity Fortress Certification
Banc de certification ultime : Validator de Chaîne, Snapshot 9/9, Restauration Atomique, Secret Exigé & Boot Attestation.
"""
import sys
import os
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_context import ImmutableIdentityContext
from core.identity.identity_guardian import IdentityGuardian
from core.identity.identity_snapshot import identity_snapshot_engine
from core.identity.identity_recovery import identity_recovery_engine
from core.identity.identity_chain import identity_chain_engine
from core.identity.identity_chain_validator import identity_chain_validator
from core.identity.boot_attestation import boot_attestation_engine
from core.identity.identity_persistence import identity_persistence

def run_fortress_certification():
    print("============================================================")
    print(" E-ZZIO V7.31 — IDENTITY FORTRESS CERTIFICATION (10/10)")
    print("============================================================\n")

    identity_file = ROOT_DIR / "runtime" / "identity" / "identity.json"

    # 1. Validation du Validator de Chaîne Historique
    pers_res = identity_persistence.build_and_seal_identity_persistence()
    chain_block = identity_chain_engine.append_identity_block(
        identity_root_hash=pers_res["identity_root_hash"],
        version="v1.0-fortress",
        description="Fortress Validation Block"
    )
    chain_val = identity_chain_validator.validate_chain()
    assert chain_val["valid"] is True, f"Chaîne invalide : {chain_val.get('error')}"
    print(f"  [1/5] Chain Validator : OK ({chain_val['block_count']} blocs vérifiés).")

    # 2. Validation du Snapshot Exhaustif (9/9)
    snap_meta = identity_snapshot_engine.create_snapshot()
    assert snap_meta["backed_up_count"] == 9, f"Snapshot incomplet : {snap_meta['backed_up_count']}/9"
    print(f"  [2/5] Full Snapshot Coverage : OK ({snap_meta['backed_up_count']}/9 artefacts archivés).")

    # 3. Validation de la Restauration Transactionnelle Atomique
    identity_file.unlink()
    rec_res = identity_recovery_engine.recover_identity_from_latest_snapshot()
    assert rec_res["recovered"] is True and rec_res.get("atomic") is True, "Échec de la restauration atomique !"
    assert identity_file.exists(), "identity.json absent après restauration atomique !"
    print("  [3/5] Atomic Transactional Recovery : OK.")

    # 4. Validation du Boot Attestation Report
    ctx = ImmutableIdentityContext()
    guardian = IdentityGuardian(ctx)
    attest = boot_attestation_engine.generate_attestation(ctx, guardian)
    assert attest["attestation_status"] == "CERTIFIED_10_10", "Attestation rejetée !"
    print(f"  [4/5] Boot Attestation Report : OK (Session {attest['boot_session_id']} certifiée).")

    # 5. Validation du Secret Maître Obligatoire
    old_env = os.environ.get("EZZIO_LEDGER_SECRET")
    try:
        os.environ.pop("EZZIO_LEDGER_SECRET", None)
        secret_failed = False
        try:
            _ = ImmutableIdentityContext()
        except ValueError:
            secret_failed = True
        assert secret_failed is True, "Le système n'a pas rejeté l'absence de secret maître !"
        print("  [5/5] Strict Secret Enforcement : OK (Démarrage sans secret bloqué).")
    finally:
        if old_env: os.environ["EZZIO_LEDGER_SECRET"] = old_env

    print("\n============================================================")
    print(" V7.31 CERTIFIÉ : COUCHE IDENTITÉ HARDENED (10/10 REEL)")
    print("============================================================\n")

if __name__ == "__main__":
    run_fortress_certification()
