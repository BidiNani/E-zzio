from __future__ import annotations
import shutil
from pathlib import Path
from typing import List

class SnapshotManager:
    """Gère l'isolation par snapshot et le rollback atomique des fichiers modifiés."""

    def __init__(self, snapshots_root: Path = Path("runtime/recovery/snapshots")):
        self.snapshots_root = snapshots_root
        self.snapshots_root.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, execution_id: str, target_paths: List[Path]) -> Path:
        """Crée une copie de sauvegarde des fichiers/dossiers cibles avant modification."""
        snap_dir = self.snapshots_root / execution_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        
        manifest = []
        for path in target_paths:
            if path.exists():
                dest = snap_dir / path.name
                if path.is_dir():
                    shutil.copytree(path, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, dest)
                manifest.append({"original": str(path), "backup": str(dest)})

        # Enregistre un manifeste de snapshot pour guider le rollback
        manifest_file = snap_dir / "manifest.json"
        import json
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return snap_dir

    def rollback(self, execution_id: str) -> bool:
        """Restaure atomiquement l'état initial des fichiers à partir du snapshot."""
        snap_dir = self.snapshots_root / execution_id
        manifest_file = snap_dir / "manifest.json"
        
        if not manifest_file.exists():
            return False

        try:
            import json
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            for entry in manifest:
                orig_path = Path(entry["original"])
                backup_path = Path(entry["backup"])
                
                if backup_path.exists():
                    if backup_path.is_dir():
                        shutil.copytree(backup_path, orig_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(backup_path, orig_path)
            return True
        except Exception:
            return False

    def purge_snapshot(self, execution_id: str):
        """Nettoie le snapshot après une exécution réussie."""
        snap_dir = self.snapshots_root / execution_id
        if snap_dir.exists():
            shutil.rmtree(snap_dir, ignore_errors=True)