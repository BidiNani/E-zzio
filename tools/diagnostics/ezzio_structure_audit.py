"""
E-ZZIO Core — Structural Hygiene Audit (V8.10.1)
Audit Read-Only de l'arborescence E-ZZIO.
Catégorise les fichiers par rôle opérationnel.
"""

import json
import os
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
AUDIT_FILE = ROOT_DIR / "EZZIO_STRUCTURE_AUDIT_V810.json"


def get_category(path: Path):
    path_str = str(path).lower()
    if "core" in path_str or "constitution" in path_str:
        return "Active Core"
    if "runtime" in path_str or "observatory" in path_str or "report" in path_str or "backup" in path_str:
        return "Operational Tools"
    if "lab" in path_str or "test" in path_str or "simulation" in path_str:
        return "Laboratory"
    if "archive" in path_str or "old" in path_str or "legacy" in path_str:
        return "Historical/Archive"
    return "Uncategorized"


def run_audit():
    audit_data = {
        "audit_timestamp": datetime.now().isoformat(),
        "categories": {"Active Core": [], "Operational Tools": [], "Laboratory": [], "Historical/Archive": [], "Uncategorized": []},
        "stats": {"total_files": 0, "total_size_mb": 0},
    }

    # Liste des dossiers à ignorer
    ignore = {".venv", ".git", "__pycache__"}

    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in ignore]
        for name in files:
            f_path = Path(root) / name
            if f_path.suffix in [".json", ".py", ".jsonl", ".md"]:
                cat = get_category(f_path)
                stats = {"path": str(f_path.relative_to(ROOT_DIR)), "size_bytes": f_path.stat().st_size}
                audit_data["categories"][cat].append(stats)
                audit_data["stats"]["total_files"] += 1
                audit_data["stats"]["total_size_mb"] += f_path.stat().st_size

    audit_data["stats"]["total_size_mb"] = round(audit_data["stats"]["total_size_mb"] / (1024 * 1024), 4)

    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print(f"[*] Audit terminé. Rapport généré : {AUDIT_FILE}")


if __name__ == "__main__":
    run_audit()
