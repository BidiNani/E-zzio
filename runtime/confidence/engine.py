"""
E-ZZIO V9.5.1 — Confidence Engine
Calcule la confiance basée sur l'historique et vérifie les invariants ECOL.
"""

import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
LEDGER_DIR = ROOT_DIR / "runtime" / "experience" / "ledger"
POLICIES_PATH = ROOT_DIR / "runtime" / "confidence" / "policies.json"


class ConfidenceEngine:
    def __init__(self):
        self.policies = json.loads(POLICIES_PATH.read_text())

    def analyze(self, workflow_id: str, plan: dict) -> dict:
        # 1. Protection Invariants (ECOL/Constitution)
        target = plan.get("target", "").lower()
        if any(inv in target for inv in self.policies["system_invariants"]):
            return {"decision": "DENIED", "reason": "SYSTEM_INVARIANT_PROTECTION"}

        # 2. Calcul du score via Ledger
        success_path = LEDGER_DIR / "workflow_success.jsonl"
        fail_path = LEDGER_DIR / "workflow_failure.jsonl"

        successes = 0
        failures = 0

        if success_path.exists():
            with open(success_path, "r") as f:
                successes = len(f.readlines())
        if fail_path.exists():
            with open(fail_path, "r") as f:
                failures = len(f.readlines())

        total = successes + failures
        if total < 5:  # Insuffisance de données
            confidence = 0.3
        else:
            confidence = successes / total

        # 3. Decision Logic
        if confidence > self.policies["high_threshold"]:
            decision = "AUTO_EXECUTE"
        elif confidence > self.policies["ask_threshold"]:
            decision = "REQUEST_APPROVAL"
        else:
            decision = "ASK"

        return {"decision": decision, "confidence": round(confidence, 2), "reason": "HISTORICAL_ANALYSIS"}
