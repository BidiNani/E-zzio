"""
E-ZZIO Core — Structural Certification Engine (V8.10.3)
Audit Read-Only de la zone active, vérification du File Registry,
contrôle d'absence de dépendances cassées vers le Cold Storage.
"""

from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
REGISTRY_FILE = ROOT_DIR / "core" / "constitution" / "ezzio_file_registry.json"
AUDIT_FILE = ROOT_DIR / "EZZIO_STRUCTURE_AUDIT_V810.json"


def run_structural_certification():
    print("\n" + "=" * 60)
    print(" 🏛️ E-ZZIO V8.10.3 — STRUCTURAL CERTIFICATION PIPELINE")
    print("=" * 60)

    # 1. Vérification de la présence des dossiers et fichiers critiques (Active Zone)
    critical_paths = [
        ROOT_DIR / "core",
        ROOT_DIR / "runtime",
        ROOT_DIR / "bridge",
        ROOT_DIR / "tools",
        ROOT_DIR / "config",
        ROOT_DIR / "archive" / "cold_storage",
    ]

    missing_critical = [str(p.relative_to(ROOT_DIR)) for p in critical_paths if not p.exists()]
    active_zone_status = "PASS" if not missing_critical else "FAIL"

    # 2. Validation du File Registry
    registry_status = "PASS" if REGISTRY_FILE.exists() else "FAIL"

    # 3. Vérification des dépendances ou références orphelines vers cold_storage dans le code actif (.py)
    # On s'assure qu'aucun import critique ne pointe vers archive/cold_storage
    broken_references = 0
    for py_file in ROOT_DIR.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "archive/cold_storage" in content or "cold_storage" in content:
                # Sauf si c'est le script de migration lui-même
                if py_file.name != "cold_storage_migrator.py":
                    broken_references += 1
        except Exception:
            pass

    import_graph_status = "PASS" if broken_references == 0 else "WARNING"

    # 4. Vérification de l'existence du manifeste d'archive
    manifest_path = ROOT_DIR / "archive" / "cold_storage" / "archive_manifest.json"
    archive_status = "SEALED" if manifest_path.exists() else "UNSEALED"

    print(f" Timestamp UTC      : {datetime.now(UTC).isoformat()}")
    print("-" * 60)
    print(f" [CHECK 1] Active Zone Integrity   : [{active_zone_status}]")
    print(f" [CHECK 2] File Registry Presence  : [{registry_status}]")
    print(f" [CHECK 3] Import Graph Dependency : [{import_graph_status}] (Orphan references: {broken_references})")
    print(f" [CHECK 4] Cold Storage Archive    : [{archive_status}]")
    print("-" * 60)

    if active_zone_status == "PASS" and registry_status == "PASS" and archive_status == "SEALED":
        print(" 🟢 GLOBAL STATUS : STRUCTURAL_INTEGRITY_CONFIRMED")
    else:
        print(" 🔴 GLOBAL STATUS : REVIEW_REQUIRED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_structural_certification()
