"""
E-ZZIO V7.59.3.2 — Cognitive Gatekeeper (Path Normalized)
Gère l'absolutisation des chemins pour éviter les erreurs ValueError de pathlib.relative_to.
"""
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
POLICY_FILE = ROOT_DIR / "runtime" / "policy" / "protected_identity_registry.json"

class CognitiveGatekeeper:
    def __init__(self):
        self.banned_extensions = {".bak", ".tmp", ".log", ".pyc", ".csv"}
        self.synthetic_markers = ["test_isolation", "sandbox", "fuzz", "stress", "chaos", "soak", "benchmark", "mock", "test_"]
        self.rpg_keywords = {
            "wow": 2, "wotlk": 3, "druid": 3, "feral": 3, "raid": 2, 
            "boss": 2, "macro": 2, "talent": 1, "gear": 1, "loot": 1, 
            "guild": 1, "instance": 1, "profession": 1, "capcap": 3, "warlock": 2
        }
        self.protected_paths = set()
        self._load_policy()

    def _load_policy(self):
        if POLICY_FILE.exists():
            try:
                with open(POLICY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.protected_paths = {p.replace("\\", "/") for p in data.get("exact_paths", [])}
            except Exception: pass

    def evaluate(self, file_path: Path, content_snippet: str = "") -> dict:
        # Normalisation robuste : transforme le chemin en absolu si nécessaire
        if not file_path.is_absolute():
            abs_path = (ROOT_DIR / file_path).resolve()
        else:
            abs_path = file_path.resolve()

        try:
            rel_path = abs_path.relative_to(ROOT_DIR.resolve()).as_posix()
        except ValueError:
            rel_path = str(file_path).replace("\\", "/")

        path_lower = str(abs_path).lower()
        content_lower = content_snippet.lower()

        # [PRIORITÉ 1] HARD LOCK Identitaire
        if rel_path in self.protected_paths:
            return {
                "promoted": True, "indexable": True, "protected": True,
                "confidence": 1.0, "importance": 10,
                "memory_type": "identity_core", "reason": "IMMUTABLE_IDENTITY"
            }

        # [PRIORITÉ 2] Blocage Bruit
        if any(marker in path_lower for marker in self.synthetic_markers):
            return {
                "promoted": False, "indexable": False, "protected": False,
                "confidence": 0.0, "importance": 0,
                "memory_type": "SYNTHETIC_NOISE", "reason": "laboratory_simulation_blocked"
            }

        # [PRIORITÉ 3] Scoring Domaine
        rpg_score = sum(weight for kw, weight in self.rpg_keywords.items() if kw in path_lower or kw in content_lower)
        if rpg_score >= 5 or ("rpg" in path_lower and rpg_score >= 3):
            return {
                "promoted": True, "indexable": True, "protected": False,
                "confidence": 0.95, "importance": 9,
                "memory_type": "RPG_MEMORY", "reason": f"rpg_domain_score_{rpg_score}"
            }

        # [PRIORITÉ 4] Classification Fine
        if "security" in path_lower or "auth" in path_lower:
            return {"promoted": True, "indexable": True, "memory_type": "security_audit", "confidence": 0.90, "importance": 7, "reason": "access_security_trace"}
        if "forensic" in path_lower or "ledger" in path_lower:
            return {"promoted": True, "indexable": True, "memory_type": "forensic_event", "confidence": 0.95, "importance": 8, "reason": "forensic_ledger_trace"}
        
        if "human_chat" in path_lower or "decision" in path_lower:
            return {"promoted": True, "indexable": True, "memory_type": "experience_ledger", "confidence": 0.90, "importance": 8, "reason": "human_interaction_ledger"}

        # [FALLBACK] QUARANTINE
        return {
            "promoted": False, "indexable": False, "protected": False,
            "confidence": 0.0, "importance": 0,
            "memory_type": "QUARANTINE", "reason": "insufficient_semantic_confidence_unknown"
        }
