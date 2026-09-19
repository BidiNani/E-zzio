"""
E-ZZIO V7.59.2 — Cognitive Taxonomy Repair & Memory Requalification
Corrige définitivement les règles d'admission du MemoryValidator :
- Exclut totalement et de force (SYNTHETIC_NOISE) tout chemin de test/sandbox/fuzz.
- Surclasse les ledgers de forensique et d'audit en 'security_audit'.
- Capture et étiquette explicitement la mémoire RPG (jeu, identité, contexte).
"""

import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"
POLICY_FILE = ROOT_DIR / "runtime" / "policy" / "protected_identity_registry.json"
TAXONOMY_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "v759_taxonomy_repair_report.json"


class TaxonomyRepairValidator:
    def __init__(self):
        self.banned_extensions = {".bak", ".tmp", ".log", ".pyc", ".csv"}
        self.banned_directories = ["archive_patches", "archive_traces", "temp", "tmp", "cache", "backup"]

        # Barrière absolue 3 : Pare-feu anti-bruit strict
        self.synthetic_markers = ["test_isolation", "sandbox", "fuzz", "stress", "chaos", "soak", "benchmark", "mock", "test_"]

        # Marqueurs de la mémoire RPG / Contexte
        self.rpg_markers = ["rpg", "wow", "wotlk", "druid", "capcap", "raid", "talent", "macro", "identity forge"]

        self.protected_paths = set()
        self._load_policy()

    def _load_policy(self):
        if POLICY_FILE.exists():
            try:
                with open(POLICY_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.protected_paths = set(data.get("exact_paths", []))
            except Exception:
                pass

    def evaluate_source(self, file_path: Path, content_snippet: str = "") -> dict:
        try:
            rel_path = file_path.relative_to(ROOT_DIR).as_posix()
        except ValueError:
            rel_path = str(file_path)

        path_lower = str(file_path).lower()
        content_lower = content_snippet.lower()

        # 1. Identité Protégée (Priorité Absolue)
        if rel_path in self.protected_paths:
            return {
                "promoted": True,
                "protected": True,
                "confidence": 1.0,
                "importance": 10,
                "memory_type": "identity_core",
                "reason": "IMMUTABLE_IDENTITY",
            }

        # 2. Barrière Anti-Bruit Absolue (SYNTHETIC_NOISE)
        if any(marker in path_lower for marker in self.synthetic_markers):
            return {
                "promoted": False,
                "protected": False,
                "confidence": 0.0,
                "importance": 0,
                "memory_type": "SYNTHETIC_NOISE",
                "reason": "laboratory_simulation_blocked",
            }

        if file_path.suffix.lower() in self.banned_extensions:
            return {"promoted": False, "memory_type": "junk", "reason": "banned_extension"}

        # 3. Capture de la mémoire RPG
        if any(marker in path_lower or marker in content_lower for marker in self.rpg_markers):
            return {
                "promoted": True,
                "protected": False,
                "confidence": 0.95,
                "importance": 9,
                "memory_type": "RPG_MEMORY",
                "reason": "rpg_genesis_captured",
            }

        # 4. Expérience vécue (Ledgers de décision)
        if "ledgers" in path_lower or "decision" in path_lower:
            return {
                "promoted": True,
                "protected": False,
                "confidence": 0.95,
                "importance": 8,
                "memory_type": "experience_ledger",
                "reason": "valid_experience_ledger",
            }

        # 5. Sécurité et Forensique (Correctement qualifiés en security_audit)
        if "security" in path_lower or "audit" in path_lower or "forensic" in path_lower or "tool_calls" in path_lower:
            return {
                "promoted": True,
                "protected": False,
                "confidence": 0.90,
                "importance": 7,
                "memory_type": "security_audit",
                "reason": "verified_security_trace",
            }

        # 6. Opérationnel par défaut
        return {
            "promoted": True,
            "protected": False,
            "confidence": 0.5,
            "importance": 5,
            "memory_type": "OPERATIONAL",
            "reason": "standard_operational",
        }


def audit_taxonomy_repair():
    print("[*] Lancement de l'audit de réparation de taxonomie...")
    validator = TaxonomyRepairValidator()

    # Simulation d'évaluation sur l'index existant pour vérifier le redressement
    if not INDEX_DB.exists():
        print("[!] Index FTS5 introuvable.")
        return

    uri = f"file:{INDEX_DB}?mode=ro"
    reclassified_counts = {}
    blocked_count = 0

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_path, content, memory_type FROM memory_search;")
        rows = cursor.fetchall()

        for source_path, content, _old_type in rows:
            dummy_path = ROOT_DIR / source_path
            evaluation = validator.evaluate_source(dummy_path, content)

            if not evaluation["promoted"]:
                blocked_count += 1
                new_type = evaluation["memory_type"]
            else:
                new_type = evaluation["memory_type"]

            reclassified_counts[new_type] = reclassified_counts.get(new_type, 0) + 1

    report = {"total_audited": len(rows), "simulated_taxonomy": reclassified_counts, "synthetic_noise_intercepted": blocked_count}

    TAXONOMY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(TAXONOMY_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(" RAPPORT DE SIMULATION DE RÉPARATION TAXONOMIQUE")
    print("=" * 50)
    print(f" Total lignes évaluées     : {len(rows)}")
    print(f" Bruit bloqué (SYNTHETIC)  : {blocked_count}")
    print("-" * 50)
    print(" NOUVELLE RÉPARTITION SIMULÉE :")
    for m_type, count in reclassified_counts.items():
        print(f"   - {m_type:<20} : {count}")
    print("-" * 50)
    print(f" Rapport de réparation généré : {TAXONOMY_REPORT}")


if __name__ == "__main__":
    audit_taxonomy_repair()
