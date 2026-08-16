import shutil
from pathlib import Path
import hashlib

class RollbackManager:
    @staticmethod
    def create_snapshot(target_path: str, root_dir: Path, snapshot_dir: Path) -> dict:
        target = root_dir / target_path
        snap_path = snapshot_dir / (target.name + ".bak")
        
        pre_hash = ""
        if target.exists():
            shutil.copy2(target, snap_path)
            pre_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        
        return {"target": target_path, "backup": str(snap_path), "pre_hash": pre_hash}

    @staticmethod
    def restore(manifest: dict, root_dir: Path):
        target = root_dir / manifest["target"]
        backup = Path(manifest["backup"])
        if backup.exists():
            shutil.move(backup, target)
