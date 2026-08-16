import time
import json
from pathlib import Path

class TrustEngine:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.states = ["TRUSTED", "DEGRADED", "QUARANTINE", "RECOVERY"]

    def _load_state(self) -> dict:
        if not self.state_file.exists():
            return {
                "score": 100,
                "state": "TRUSTED",
                "confidence": "HIGH",
                "history": []
            }
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"score": 100, "state": "TRUSTED", "confidence": "HIGH", "history": []}

    def _save_state(self, state_data: dict):
        self.state_file.write_text(json.dumps(state_data, indent=4, ensure_ascii=False), encoding="utf-8")

    def evaluate_trust(self, ledger_valid: bool, snapshot_matched: bool, drifts: list) -> dict:
        """
        Calcule le Trust Score, évalue la machine à états de quarantaine 
        et consigne les deltas explicables.
        """
        current_data = self._load_state()
        previous_score = current_data["score"]
        
        # 1. Calcul des composantes du score (Max 100)
        score = 0
        events = []

        if ledger_valid:
            score += 30
        else:
            events.append({"type": "LEDGER_INVALID", "impact": -30})

        if snapshot_matched:
            score += 20
        else:
            events.append({"type": "SNAPSHOT_MISMATCH", "impact": -20})

        # Évaluation des dérives matérielles transmises par le registre
        drift_penalty = 0
        for drift in drifts:
            if "THREADS" in drift or "SMT" in drift or "CORES" in drift:
                drift_penalty += 45  # Ajusté pour faire chuter le score sous 60 -> QUARANTINE
                events.append({"type": f"CRITICAL_DRIFT_{drift}", "impact": -45})
            else:
                drift_penalty += 10
                events.append({"type": f"MINOR_DRIFT_{drift}", "impact": -10})

        score = max(0, 50 + 30 + 20 - drift_penalty) # Base 100 max pondérée
        if not ledger_valid: score = min(score, 40)
        if not snapshot_matched: score = min(score, 60)

        # 2. Détermination de l'état de la machine à états (Quarantine State Machine)
        if score >= 85:
            new_state = "TRUSTED"
            confidence = "HIGH"
        elif 60 <= score < 85:
            new_state = "DEGRADED"
            confidence = "MEDIUM"
        else:
            new_state = "QUARANTINE"
            confidence = "LOW"

        # Gestion de l'état RECOVERY si on revient d'une quarantaine
        if current_data["state"] == "QUARANTINE" and new_state == "TRUSTED":
            new_state = "RECOVERY"

        # 3. Construction du Delta Ledger (Explainability)
        delta_record = {
            "timestamp": time.time(),
            "previous_score": previous_score,
            "current_score": score,
            "previous_state": current_data["state"],
            "current_state": new_state,
            "events": events
        }

        current_data["score"] = score
        current_data["state"] = new_state
        current_data["confidence"] = confidence
        current_data["history"].append(delta_record)

        self._save_state(current_data)

        return {
            "trust_score": score,
            "state": new_state,
            "confidence": confidence,
            "routing_allowed": new_state in ["TRUSTED", "RECOVERY"],
            "quarantine_active": new_state == "QUARANTINE",
            "audit_trail": delta_record
        }
