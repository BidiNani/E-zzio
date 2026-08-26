"""
E-ZZIO V7.31 — Identity Chain Validator
Vérifie la continuité cryptographique, l'absence de rupture et l'intégrité de la chaîne d'identité.
"""

import json
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CHAIN_FILE = ROOT_DIR / "runtime" / "identity" / "identity_chain.jsonl"


class IdentityChainValidator:
    @staticmethod
    def validate_chain() -> dict:
        if not CHAIN_FILE.exists():
            return {"valid": False, "block_count": 0, "error": "CHAIN_FILE_MISSING"}

        lines = CHAIN_FILE.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return {"valid": False, "block_count": 0, "error": "CHAIN_FILE_EMPTY"}

        expected_index = 0
        expected_previous_hash = "0" * 64

        for idx, line in enumerate(lines):
            try:
                block = json.loads(line)
            except Exception:
                return {"valid": False, "broken_at_block": idx, "error": f"CORRUPTED_JSON_AT_LINE_{idx + 1}"}

            b_index = block.get("block_index")
            b_prev = block.get("previous_hash")
            b_hash = block.get("block_hash")
            b_root = block.get("identity_root_hash")
            b_ver = block.get("version")

            if b_index != expected_index:
                return {"valid": False, "broken_at_block": idx, "error": f"INDEX_GAP_EXPECTED_{expected_index}_GOT_{b_index}"}

            if b_prev != expected_previous_hash:
                return {"valid": False, "broken_at_block": idx, "error": f"PREVIOUS_HASH_MISMATCH_AT_BLOCK_{b_index}"}

            # Recalcul du hash de bloc
            raw_payload = f"{b_index}:{b_prev}:{b_root}:{b_ver}"
            recalculated_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

            if recalculated_hash != b_hash:
                return {"valid": False, "broken_at_block": idx, "error": f"BLOCK_HASH_INVALID_AT_BLOCK_{b_index}"}

            expected_index += 1
            expected_previous_hash = b_hash

        return {"valid": True, "block_count": len(lines), "last_block_hash": expected_previous_hash, "error": None}


identity_chain_validator = IdentityChainValidator()
