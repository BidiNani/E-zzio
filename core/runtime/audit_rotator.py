"""
E-ZZIO V7.47 — Audit Log Rotator
Assure la rotation, l'archivage et le nettoyage des fichiers d'audit JSONL.
"""

import shutil
from pathlib import Path
from datetime import datetime, timezone


class AuditRotator:
    def __init__(self, audit_dir: Path):
        self.audit_dir = audit_dir
        self.archive_dir = audit_dir / "archives"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def rotate_logs(self, max_size_bytes: int = 10 * 1024 * 1024) -> list:
        rotated_files = []
        if not self.audit_dir.exists():
            return rotated_files

        for file_path in self.audit_dir.glob("*.jsonl"):
            if file_path.is_file() and file_path.stat().st_size > max_size_bytes:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                archive_name = f"{file_path.stem}_{timestamp}.archive"
                dest_path = self.archive_dir / archive_name

                shutil.move(str(file_path), str(dest_path))
                file_path.touch()  # Recrée un fichier vide propre
                rotated_files.append(str(file_path.name))

        return rotated_files


audit_rotator = AuditRotator(Path(r"G:\AI\E-zzio\runtime\audit\discord"))
