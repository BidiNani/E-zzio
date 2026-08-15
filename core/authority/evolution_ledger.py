"""
E-ZZIO V7.32 — Evolution Ledger
Enregistre chaque évolution validée dans une chaîne de blocs immuable.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LEDGER_FILE = ROOT_DIR / "runtime" / "evolution" / "ledger" / "evolution_ledger.jsonl"

class EvolutionLedger:
    def __init__(self):
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _get_last_block(self) -> dict:
        if not LEDGER_FILE.exists():
            return None
        lines = LEDGER_FILE.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        return json.loads(lines[-1])

    def append_block(self, change_target: str, validation_status: str, artifact_hash: str) -> dict:
        last_block = self._get_last_block()
        block_index = 0 if last_block is None else last_block.get("block_index", 0) + 1
        previous_hash = "0" * 64 if last_block is None else last_block.get("block_hash")

        raw_payload = f"{block_index}:{previous_hash}:{change_target}:{validation_status}:{artifact_hash}"
        block_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        block_data = {
            "block_index": block_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_hash": previous_hash,
            "change": change_target,
            "validation": validation_status,
            "artifact_hash": artifact_hash,
            "block_hash": block_hash
        }

        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(block_data, ensure_ascii=False) + "\n")

        return block_data

evolution_ledger = EvolutionLedger()
