import os
import json
import hashlib
from pathlib import Path

class SegmentedRecoveryEngine:
    def __init__(self, store_root: str, max_segment_size: int = 10 * 1024 * 1024):
        self.store_root = Path(store_root)
        self.segments_dir = self.store_root / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_root / "manifest.json"
        self.manifest_sha_path = self.store_root / "manifest.json.sha256"
        self.max_segment_size = max_segment_size
        
        self.manifest = self._load_and_validate_manifest()

    def _verify_manifest_checksum(self) -> bool:
        """Vérifie l'intégrité du manifeste via son fichier sidecar SHA256."""
        if not self.manifest_path.exists() or not self.manifest_sha_path.exists():
            return False
        try:
            expected_sha = self.manifest_sha_path.read_text(encoding="utf-8").strip()
            sha = hashlib.sha256()
            with open(self.manifest_path, "rb") as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            return sha.hexdigest() == expected_sha
        except Exception:
            return False

    def _load_and_validate_manifest(self) -> dict:
        """Charge le manifeste si son checksum est valide, sinon lance la reconstruction."""
        if self._verify_manifest_checksum():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "active_segment_id" in data and "segments" in data:
                        print("[CACHE] Manifeste valide chargé instantanément (Checksum OK).")
                        return data
            except Exception:
                pass
        
        print("[AVERTISSEMENT] Manifeste absent, corrompu ou altéré. Reconstruction d'urgence...")
        return self._reconstruct_manifest_from_disk()

    def _reconstruct_manifest_from_disk(self) -> dict:
        segments_meta = []
        max_id = 0
        
        if self.segments_dir.exists():
            segment_files = sorted(self.segments_dir.glob("segment_*.jsonl"))
            for p in segment_files:
                try:
                    parts = p.stem.split("_")
                    seg_id = int(parts[1])
                    max_id = max(max_id, seg_id)
                except Exception:
                    continue

                self._sanitize_segment_eof(p)
                
                file_size = p.stat().st_size
                if file_size == 0:
                    continue

                sha = hashlib.sha256()
                with open(p, "rb") as f:
                    while chunk := f.read(8192):
                        sha.update(chunk)
                
                # Tous les segments scannés sur le disque hors actif sont SEALED & VERIFIED
                segments_meta.append({
                    "id": seg_id,
                    "file": p.name,
                    "size": file_size,
                    "state": "VERIFIED",
                    "sha256": sha.hexdigest()
                })

        active_id = max_id if max_id > 0 else 1
        closed_segments = []
        
        if segments_meta:
            # Le dernier segment devient l'ACTIVE, les précédents sont SEALED
            last_seg = segments_meta[-1]
            last_seg["state"] = "ACTIVE"
            last_seg.pop("sha256", None) # Un segment actif n'a pas de SHA256 figé
            
            closed_segments = segments_meta[:-1]
            for s in closed_segments:
                s["state"] = "SEALED"
            active_id = last_seg["id"]

        new_manifest = {
            "active_segment_id": active_id,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": closed_segments
        }
        
        self.manifest = new_manifest
        self._save_manifest()
        print(f"[RECOVERY] Manifeste reconstruit. Segment actif ID : {active_id} (État: ACTIVE)")
        return new_manifest

    def _sanitize_segment_eof(self, file_path: Path):
        if not file_path.exists() or file_path.stat().st_size == 0:
            return

        valid_lines = []
        try:
            with open(file_path, "rb") as f:
                raw = f.read()

            lines = raw.split(b"\n")
            for index, raw_line in enumerate(lines):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    decoded = stripped.decode("utf-8")
                    json.loads(decoded)
                    valid_lines.append(decoded)
                except Exception:
                    if index == len(lines) - 1:
                        print(f"[QUARANTAINE] EOF tronqué purgé dans {file_path.name}")
                        break
                    else:
                        raise RuntimeError(f"Corruption interne dans {file_path.name}")
        except Exception:
            return

        with open(file_path, "w", encoding="utf-8") as f:
            for line in valid_lines:
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _save_manifest(self):
        """Sauvegarde le manifeste et met à jour son checksum sidecar."""
        temp_manifest = self.manifest_path.with_suffix(".tmp")
        with open(temp_manifest, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_manifest, self.manifest_path)

        # Calcul et écriture du sidecar SHA256 du manifeste
        sha = hashlib.sha256()
        with open(self.manifest_path, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        
        self.manifest_sha_path.write_text(sha.hexdigest(), encoding="utf-8")
