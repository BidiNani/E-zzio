import os
import json
import hashlib
from pathlib import Path

class SegmentManager:
    def __init__(self, store_root: str, max_segment_size: int = 10 * 1024 * 1024):
        self.store_root = Path(store_root)
        self.segments_dir = self.store_root / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_root / "manifest.json"
        self.max_segment_size = max_segment_size
        
        self.manifest = self._load_or_init_manifest()

    def _load_or_init_manifest(self) -> dict:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Initialisation par défaut
        return {
            "active_segment_id": 1,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": []
        }

    def _save_manifest(self):
        temp_manifest = self.manifest_path.with_suffix(".tmp")
        with open(temp_manifest, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_manifest, self.manifest_path)

    def get_active_segment_path(self) -> Path:
        active_id = self.manifest["active_segment_id"]
        filename = f"segment_{active_id:06d}.jsonl"
        return self.segments_dir / filename

    def check_rotation_needed(self, current_batch_size: int) -> bool:
        path = self.get_active_segment_path()
        if not path.exists():
            return False
        return (path.stat().st_size + current_batch_size) > self.max_segment_size

    def rotate_segment(self):
        active_id = self.manifest["active_segment_id"]
        old_path = self.get_active_segment_path()
        
        # Calcul du SHA256 du segment clos
        file_hash = ""
        file_size = 0
        if old_path.exists():
            file_size = old_path.stat().st_size
            sha = hashlib.sha256()
            with open(old_path, "rb") as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            file_hash = sha.hexdigest()

        # Enregistrement dans le manifeste
        seg_entry = {
            "id": active_id,
            "file": old_path.name,
            "size": file_size,
            "sha256": file_hash
        }
        
        # Mise à jour de la liste des segments
        self.manifest["segments"] = [s for s in self.manifest["segments"] if s["id"] != active_id]
        self.manifest["segments"].append(seg_entry)

        # Passage au segment suivant
        self.manifest["active_segment_id"] = active_id + 1
        self._save_manifest()
