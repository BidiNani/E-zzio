import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("ezzio.core.cleanup")


class SystemCleanupService:
    """Service de nettoyage déterministe des artefacts et du bruit résiduel."""

    ARCHIVE_DIRS = {
        "_archive",
        "_archive_memoire_morte",
        "_a_verifier",
        "_backups_auto",
        "runtime_temp_forensic",
        "quarantine",
        "guardian",
    }
    LOG_EXTENSIONS = {".log", ".tmp", ".bak", ".old"}

    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()

    def run_cleanup(
        self, dry_run: bool = True, remove_logs: bool = True, remove_temp: bool = True, remove_archives: bool = True
    ) -> dict[str, Any]:
        folders_removed: list[str] = []
        folders_skipped: list[str] = []
        files_removed: list[str] = []
        files_skipped: list[str] = []
        space_freed = 0

        # 1. Dossiers archives & scratch
        if remove_archives:
            for dir_name in self.ARCHIVE_DIRS:
                for dir_path in self.root.rglob(dir_name):
                    if dir_path.is_dir() and ".venv" not in dir_path.parts:
                        try:
                            size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                            rel_dir = str(dir_path.relative_to(self.root)).replace("\\", "/")
                            if not dry_run:
                                shutil.rmtree(dir_path, ignore_errors=True)
                            folders_removed.append(rel_dir)
                            space_freed += size
                        except Exception as e:
                            logger.warning("Impossible de purger %s: %s", dir_path, e)
                            folders_skipped.append(str(dir_path.relative_to(self.root)).replace("\\", "/"))

        # 2. Fichiers logs & temporaires
        if remove_logs or remove_temp:
            for file_path in self.root.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.LOG_EXTENSIONS:
                    if ".venv" in file_path.parts:
                        continue

                    rel_file = str(file_path.relative_to(self.root)).replace("\\", "/")

                    # Protection contre la suppression de logs actifs verrouillés
                    if any(active in file_path.name for active in ["discord.log", "uvicorn.log"]):
                        files_skipped.append(f"{rel_file} (actif)")
                        continue

                    try:
                        size = file_path.stat().st_size
                        if not dry_run:
                            file_path.unlink(missing_ok=True)
                        files_removed.append(rel_file)
                        space_freed += size
                    except Exception as e:
                        logger.warning("Fichier verrouillé ou inaccessible %s: %s", file_path, e)
                        files_skipped.append(rel_file)

        return {
            "folders_removed": sorted(folders_removed),
            "folders_skipped": sorted(folders_skipped),
            "files_removed": sorted(files_removed),
            "files_skipped": sorted(files_skipped),
            "space_freed_bytes": space_freed,
        }
