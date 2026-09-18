"""
E-ZZIO Security — Content-Addressable Storage (CAS) Deduplicated Backup Engine.
Garantit des sauvegardes fiables, mathématiquement dédupliquées et protégées contre l'auto-réplication :
1. Architecture CAS (Content-Addressable Storage) : chaque fichier unique est stocké une seule fois par son hash SHA-256
2. Déduplication réelle entre snapshots successifs (zéro duplication physique des fichiers inchangés)
3. Manifestes de snapshot légers en JSON liant l'arborescence aux objets CAS
4. Restauration fidèle et calcul précis du ratio de déduplication
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import zlib
from pathlib import Path
from typing import Any

logger = logging.getLogger("BackupEngine")


class BackupEngine:
    EXCLUDED_PATTERNS = {
        "runtime/backups",
        "runtime/test_tmp",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".venv",
        "node_modules"
    }

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.backups_dir = (self.workspace_root / "runtime" / "backups").resolve()
        self.objects_dir = self.backups_dir / "cas" / "objects"
        self.snapshots_dir = self.backups_dir / "snapshots"

        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _is_excluded(self, path: Path) -> bool:
        """Vérifie si un chemin doit être exclu pour éviter l'auto-réplication récursive."""
        try:
            rel_str = str(path.relative_to(self.workspace_root)).replace("\\", "/")
        except ValueError:
            return True

        for exc in self.EXCLUDED_PATTERNS:
            if rel_str == exc or rel_str.startswith(exc + "/") or f"/{exc}/" in f"/{rel_str}/":
                return True
        return False

    def _store_blob(self, raw_bytes: bytes) -> tuple[str, int, bool]:
        """
        Stocke un blob dans le CAS s'il n'existe pas déjà.
        Retourne (sha256_hash, stored_bytes, is_new).
        """
        sha = hashlib.sha256(raw_bytes).hexdigest()
        prefix = sha[:2]
        bucket = self.objects_dir / prefix
        bucket.mkdir(parents=True, exist_ok=True)
        obj_file = bucket / f"{sha}.blob"

        if obj_file.exists():
            return sha, obj_file.stat().st_size, False

        compressed = zlib.compress(raw_bytes, level=6)
        obj_file.write_bytes(compressed)
        return sha, len(compressed), True

    def _read_blob(self, sha: str) -> bytes | None:
        """Lit et décompresse un blob depuis le CAS."""
        prefix = sha[:2]
        obj_file = self.objects_dir / prefix / f"{sha}.blob"
        if not obj_file.exists():
            return None
        return zlib.decompress(obj_file.read_bytes())

    def create_snapshot(self, label: str = "manual") -> dict[str, Any]:
        """Crée un snapshot dédupliqué du workspace via le CAS."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        clean_label = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in label)
        snap_id = f"snapshot_{timestamp}_{clean_label}"
        manifest_file = self.snapshots_dir / f"{snap_id}.json"

        manifest: dict[str, Any] = {
            "snapshot_id": snap_id,
            "timestamp": time.time(),
            "label": clean_label,
            "workspace_root": str(self.workspace_root),
            "files": {},
            "total_logical_bytes": 0,
            "new_objects_stored": 0,
            "dedup_objects_reused": 0,
            "physical_bytes_written": 0
        }

        try:
            for root, dirs, files in os.walk(self.workspace_root):
                dirs[:] = [d for d in dirs if not self._is_excluded(Path(root) / d)]

                for file in files:
                    file_path = Path(root) / file
                    if self._is_excluded(file_path):
                        continue

                    rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
                    raw_bytes = file_path.read_bytes()
                    file_size = len(raw_bytes)

                    sha, stored_bytes, is_new = self._store_blob(raw_bytes)

                    manifest["files"][rel_path] = {
                        "hash": sha,
                        "size": file_size,
                        "mtime": file_path.stat().st_mtime
                    }
                    manifest["total_logical_bytes"] += file_size

                    if is_new:
                        manifest["new_objects_stored"] += 1
                        manifest["physical_bytes_written"] += stored_bytes
                    else:
                        manifest["dedup_objects_reused"] += 1

            manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

            return {
                "ok": True,
                "snapshot_id": snap_id,
                "manifest_path": str(manifest_file),
                "total_files": len(manifest["files"]),
                "logical_bytes": manifest["total_logical_bytes"],
                "new_objects_stored": manifest["new_objects_stored"],
                "dedup_objects_reused": manifest["dedup_objects_reused"],
                "physical_bytes_written": manifest["physical_bytes_written"],
                "dedup_ratio": round(
                    manifest["dedup_objects_reused"] / max(1, len(manifest["files"])), 2
                )
            }

        except Exception as exc:
            logger.error("[CAS-BACKUP-ERROR] Échec de snapshot dédupliqué : %s", exc)
            return {"ok": False, "error": str(exc)}

    def restore_file(self, snapshot_id: str, rel_path: str, dest_path: Path | str) -> bool:
        """Restaure un fichier spécifique depuis un snapshot CAS."""
        manifest_file = self.snapshots_dir / f"{snapshot_id}.json"
        if not manifest_file.exists():
            return False

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        file_info = manifest.get("files", {}).get(rel_path.replace("\\", "/"))
        if not file_info:
            return False

        blob_bytes = self._read_blob(file_info["hash"])
        if blob_bytes is None:
            return False

        dst = Path(dest_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(blob_bytes)
        return True


# Singleton global
backup_engine = BackupEngine()
