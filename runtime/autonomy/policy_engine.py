"""
E-ZZIO V9.5.3 — Action Policy Engine
Classifie les actions et applique les niveaux d'autonomie (AUTO_ALLOWED, APPROVAL_REQUIRED, HUMAN_ONLY).
"""
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
REGISTRY_PATH = ROOT_DIR / "runtime" / "autonomy" / "autonomy_registry.json"

class ActionPolicyEngine:
    def __init__(self):
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def evaluate_action(self, intent_type: str, confidence: float) -> dict:
        # Vérification des invariants / actions critiques directes
        if "PROTECTED" in intent_type or "SYSTEM" in intent_type or "ECOL" in intent_type:
            return {
                "autonomy_level": "HUMAN_ONLY",
                "action": "DENIED",
                "reason": "SYSTEM_INVARIANT_PROTECTION"
            }

        # Récupération de la politique dans le registre
        policy = self.registry.get(intent_type)
        if not policy:
            # Par défaut sécurisé : si non répertorié, validation humaine requise
            return {
                "autonomy_level": "APPROVAL_REQUIRED",
                "action": "PROPOSAL_READY",
                "reason": "UNKNOWN_ACTION_DEFAULT_TO_APPROVAL"
            }

        level = policy.get("autonomy_level")

        if level == "AUTO_ALLOWED":
            req_conf = policy.get("confidence_required", 0.85)
            if confidence >= req_conf:
                return {
                    "autonomy_level": "AUTO_ALLOWED",
                    "action": "AUTO_EXECUTE",
                    "reason": "CONFIDENCE_THRESHOLD_MET"
                }
            else:
                return {
                    "autonomy_level": "AUTO_ALLOWED",
                    "action": "REQUEST_APPROVAL",
                    "reason": "CONFIDENCE_BELOW_THRESHOLD"
                }

        elif level == "APPROVAL_REQUIRED":
            return {
                "autonomy_level": "APPROVAL_REQUIRED",
                "action": "PROPOSAL_READY",
                "reason": "POLICY_MANDATES_APPROVAL"
            }

        elif level == "HUMAN_ONLY":
            return {
                "autonomy_level": "HUMAN_ONLY",
                "action": "DENIED",
                "reason": "CRITICAL_ACTION_RESTRICTED"
            }

        return {
            "autonomy_level": "APPROVAL_REQUIRED",
            "action": "PROPOSAL_READY",
            "reason": "FALLBACK_RESTRICTION"
        }
