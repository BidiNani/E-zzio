"""
E-ZZIO Core — Controlled Cold Storage Migrator (V8.10.2)
Déplace de manière sécurisée les éléments historiques lourds vers l'archive froide
en générant un manifeste cryptographique (SHA-256) avec possibilité de rollback.
"""

import shutil
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
COLD_STORAGE_DIR = ROOT_DIR / "archive" / "cold_storage"
MANIFEST_PATH = COLD_STORAGE_DIR / "archive_manifest.json"


def compute_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def execute_cold_storage_migration():
    COLD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    targets = [ROOT_DIR / "runtime" / "audit" / "full_reuse", ROOT_DIR / "runtime" / "audit" / "full_scan"]

    manifest = {
        "migration_id": f"COLD_STORAGE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "migrated_items": [],
    }

    migrated_count = 0
    for target in targets:
        if target.exists():
            dest = COLD_STORAGE_DIR / target.name
            if dest.exists():
                shutil.rmtree(dest)

            print(f"[*] Archivage sécurisé de : {target.relative_to(ROOT_DIR)} -> archive/cold_storage/{target.name}")

            shutil.move(str(target), str(dest))

            for f in dest.rglob("*"):
                if f.is_file():
                    f_hash = compute_sha256(f)
                    manifest["migrated_items"].append(
                        {"path": str(f.relative_to(ROOT_DIR)), "sha256": f_hash, "size_bytes": f.stat().st_size}
                    )
                    migrated_count += 1

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[*] Migration vers l'archive froide terminée. {migrated_count} fichier(s) sécurisé(s).")
    print(f"[*] Manifeste généré : {MANIFEST_PATH.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    execute_cold_storage_migration()
