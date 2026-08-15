"""
E-ZZIO V7.32 — Promotion Controller
Gère la promotion sécurisée des candidats et le rollback vers les snapshots V7.31.
"""
import json
import hashlib
from pathlib import Path
from core.identity.identity_snapshot import identity_snapshot_engine
from core.identity.identity_recovery import identity_recovery_engine
from core.authority.evolution_ledger import evolution_ledger

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CANDIDATES_DIR = ROOT_DIR / "runtime" / "evolution" / "candidates"
PROMOTED_DIR = ROOT_DIR / "runtime" / "evolution" / "promoted"

class PromotionController:
    def __init__(self):
        CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
        PROMOTED_DIR.mkdir(parents=True, exist_ok=True)

    def promote_candidate(self, candidate_name: str, content: str, approved_by_mentor: bool = False) -> dict:
        pre_snapshot = identity_snapshot_engine.create_snapshot()

        candidate_path = CANDIDATES_DIR / candidate_name
        candidate_path.write_text(content, encoding="utf-8")
        artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        validation_status = "PASSED" if approved_by_mentor else "REJECTED_UNAPPROVED"
        if not approved_by_mentor:
            return {"promoted": False, "reason": "MENTOR_APPROVAL_REQUIRED", "pre_snapshot": pre_snapshot["snapshot_index"]}

        promoted_path = PROMOTED_DIR / candidate_name
        promoted_path.write_text(content, encoding="utf-8")

        block = evolution_ledger.append_block(
            change_target=candidate_name,
            validation_status=validation_status,
            artifact_hash=artifact_hash
        )

        post_snapshot = identity_snapshot_engine.create_snapshot()

        return {
            "promoted": True,
            "candidate": candidate_name,
            "artifact_hash": artifact_hash,
            "ledger_block": block["block_index"],
            "pre_snapshot": pre_snapshot["snapshot_index"],
            "post_snapshot": post_snapshot["snapshot_index"]
        }

    def rollback_to_last_snapshot(self) -> dict:
        return identity_recovery_engine.recover_identity_from_latest_snapshot()

promotion_controller = PromotionController()
