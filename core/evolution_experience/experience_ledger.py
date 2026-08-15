"""
E-ZZIO V7.36 — Evolution Experience Ledger
Enregistre le cycle de vie complet d'une proposition et assure le suivi post-déploiement (Runtime Outcome).
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
EXPERIENCE_FILE = ROOT_DIR / "runtime" / "evolution" / "experience" / "experience_registry.jsonl"

class EvolutionExperienceLedger:
    def __init__(self):
        EXPERIENCE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def record_proposal(self, evolution_id: str, candidate_hash: str, scores: dict, simulation_res: dict, decision: str) -> dict:
        record = {
            "evolution_id": evolution_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "candidate_hash": candidate_hash,
            "scores": scores,
            "simulation_result": simulation_res,
            "promotion_decision": decision,
            "runtime_outcome": "PENDING"
        }
        with open(EXPERIENCE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def update_outcome(self, evolution_id: str, runtime_outcome: str) -> bool:
        if not EXPERIENCE_FILE.exists():
            return False
        
        lines = EXPERIENCE_FILE.read_text(encoding="utf-8").strip().splitlines()
        updated = False
        new_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("evolution_id") == evolution_id:
                data["runtime_outcome"] = runtime_outcome
                updated = True
            new_lines.append(json.dumps(data, ensure_ascii=False))
        
        if updated:
            EXPERIENCE_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return updated

    def get_history(self) -> list:
        if not EXPERIENCE_FILE.exists():
            return []
        return [json.loads(line) for line in EXPERIENCE_FILE.read_text(encoding="utf-8").strip().splitlines() if line.strip()]

evolution_experience_ledger = EvolutionExperienceLedger()
