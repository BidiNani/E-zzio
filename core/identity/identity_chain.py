"""
E-ZZIO V7.30 — Identity Chain of Trust Engine
Gère le registre immuable des blocs d'évolution identitaire (Genesis -> Blocks).
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CHAIN_FILE = ROOT_DIR / "runtime" / "identity" / "identity_chain.jsonl"


class IdentityChainEngine:
    def __init__(self):
        CHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _get_last_block(self) -> dict:
        if not CHAIN_FILE.exists():
            return None
        lines = CHAIN_FILE.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        return json.loads(lines[-1])

    def append_identity_block(self, identity_root_hash: str, version: str, description: str) -> dict:
        last_block = self._get_last_block()

        if last_block is None:
            block_index = 0
            previous_hash = "0" * 64
        else:
            block_index = last_block.get("block_index", 0) + 1
            previous_hash = last_block.get("block_hash")

        raw_payload = f"{block_index}:{previous_hash}:{identity_root_hash}:{version}"
        block_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        block_data = {
            "block_index": block_index,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": version,
            "description": description,
            "identity_root_hash": identity_root_hash,
            "previous_hash": previous_hash,
            "block_hash": block_hash,
        }

        with open(CHAIN_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(block_data, ensure_ascii=False) + "\n")

        return block_data


identity_chain_engine = IdentityChainEngine()
