"""
E-ZZIO V7.57.1 — Cognitive Memory Validator
Intègre le Pare-Feu Cognitif pour exclure les données de laboratoire (synthetic_test_data).
"""
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
POLICY_FILE = ROOT_DIR / "runtime" / "policy" / "protected_identity_registry.json"

class MemoryValidator:
    def __init__(self):
        self.banned_extensions = {".bak", ".tmp", ".log", ".pyc", ".csv"}
        self.banned_directories = ["archive_patches", "archive_traces", "temp", "tmp", "cache", "backup"]
        self.synthetic_markers = ["test_isolation", "sandbox", "fuzz", "stress", "chaos", "soak", "benchmark"]
        self.protected_paths = set()
        self._load_policy()

    def _load_policy(self):
        if POLICY_FILE.exists():
            try:
                with open(POLICY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.protected_paths = set(data.get("exact_paths", []))
            except Exception:
                pass

    def evaluate_source(self, file_path: Path) -> dict:
        try:
            rel_path = file_path.relative_to(ROOT_DIR).as_posix()
        except ValueError:
            rel_path = str(file_path)

        path_str = str(file_path).lower()

        # 1. Identité Protégée (Priorité Absolue)
        if rel_path in self.protected_paths:
            return {
                "promoted": True,
                "protected": True,
                "confidence": 1.0,
                "importance": 10,
                "memory_type": "identity_core",
                "reason": "IMMUTABLE_IDENTITY"
            }

        # 2. Filtres standard (Bruit et Cache)
        if file_path.suffix.lower() in self.banned_extensions:
            return {"promoted": False, "reason": f"banned_extension_{file_path.suffix.lower()[1:]}", "memory_type": "junk"}
            
        if any(banned_dir in file_path.parts for banned_dir in self.banned_directories):
            return {"promoted": False, "reason": "archived_or_temporary", "memory_type": "junk"}

        # 3. Pare-Feu Cognitif (Données de Laboratoire)
        if any(marker in path_str for marker in self.synthetic_markers):
            return {
                "promoted": False,
                "reason": "synthetic_test_data",
                "memory_type": "laboratory_trace"
            }

        # 4. Évaluation classique
        confidence, importance, memory_type = 0.5, 5, "generic"

        if "ledgers" in path_str or "decision" in path_str:
            confidence, importance, memory_type = 0.95, 8, "experience_ledger"
        elif "audit" in file_path.parts:
            confidence, importance, memory_type = 0.98, 9, "security_audit"
        elif file_path.suffix == ".py" and "core" in file_path.parts:
            confidence, importance, memory_type = 0.90, 8, "kernel_logic"

        return {
            "promoted": True,
            "protected": False,
            "confidence": confidence,
            "importance": importance,
            "memory_type": memory_type,
            "reason": "standard_validation"
        }
