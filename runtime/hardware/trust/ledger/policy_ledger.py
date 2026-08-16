import json
import time
from pathlib import Path

class PolicyAuditLedger:
    def __init__(self, ledger_file: Path):
        self.ledger_file = ledger_file
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

    def log_decision(self, trust_context: dict, request: dict, decision_result: dict, policy_version: str):
        record = {
            "timestamp": time.time(),
            "trust_before": {
                "score": trust_context.get("trust_score"),
                "state": trust_context.get("state")
            },
            "workload": {
                "workload_id": request.get("workload_id"),
                "profile": request.get("profile")
            },
            "decision": decision_result.get("decision"),
            "constraints": decision_result.get("constraints", {}),
            "policy_version": policy_version,
            "reason": decision_result.get("reason")
        }
        
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
        return record
