import os
import json
import hashlib
import queue
import threading
import time
from pathlib import Path
import psutil

class ConcurrentSegmentedEngine:
    def __init__(self, store_root: str, max_segment_size: int = 5 * 1024 * 1024, max_batch_size: int = 1000, max_batch_delay: float = 0.02):
        self.store_root = Path(store_root)
        self.segments_dir = self.store_root / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_root / "manifest.json"
        self.manifest_sha_path = self.store_root / "manifest.json.sha256"
        self.max_segment_size = max_segment_size
        
        self.max_batch_size = max_batch_size
        self.max_batch_delay = max_batch_delay
        
        self.queue = queue.Queue(maxsize=50000)
        self._stop_event = threading.Event()
        self.accepting = True
        
        # Chargement et validation durcie (Hardened Recovery)
        self.manifest = self._load_and_validate_manifest()
        
        # Démarrage du Commit Worker unique en aval
        self.commit_thread = threading.Thread(target=self._commit_loop, daemon=True)
        self.commit_thread.start()

    def _verify_manifest_checksum(self) -> bool:
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
        if self._verify_manifest_checksum():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Vérification croisée de la taille des segments SEALED avec le disque
                    for seg in data.get("segments", []):
                        seg_path = self.segments_dir / seg["file"]
                        if seg_path.exists() and seg_path.stat().st_size != seg["size"]:
                            print(f"[AVERTISSEMENT] Incohérence de taille détectée sur {seg['file']}. Reconstruction...")
                            return self._reconstruct_manifest_from_disk()
                    return data
            except Exception:
                pass
        
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
                
                segments_meta.append({
                    "id": seg_id,
                    "file": p.name,
                    "size": file_size,
                    "state": "SEALED",
                    "sealed": True,
                    "sha256": sha.hexdigest()
                })

        active_id = (max_id + 1) if segments_meta else 1
        closed_segments = segments_meta

        new_manifest = {
            "active_segment_id": active_id,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": closed_segments
        }
        
        self.manifest = new_manifest
        self._save_manifest_atomic()
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
                        break
                    else:
                        raise RuntimeError()
        except Exception:
            return

        with open(file_path, "w", encoding="utf-8") as f:
            for line in valid_lines:
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _save_manifest_atomic(self):
        """Sauvegarde atomique combinée : Manifeste + Sidecar SHA256 simultanés."""
        temp_manifest = self.manifest_path.with_suffix(".json.tmp")
        temp_sha = self.manifest_sha_path.with_suffix(".sha256.tmp")
        
        manifest_data = json.dumps(self.manifest, indent=2)
        
        # 1. Écriture fichier temporaire manifeste
        with open(temp_manifest, "w", encoding="utf-8") as f:
            f.write(manifest_data)
            f.flush()
            os.fsync(f.fileno())

        # 2. Calcul et écriture temporaire du SHA256
        sha = hashlib.sha256()
        sha.update(manifest_data.encode("utf-8"))
        sha_digest = sha.hexdigest()
        
        with open(temp_sha, "w", encoding="utf-8") as f:
            f.write(sha_digest)
            f.flush()
            os.fsync(f.fileno())

        # 3. Swap atomique synchrone des deux fichiers
        os.replace(temp_manifest, self.manifest_path)
        os.replace(temp_sha, self.manifest_sha_path)

    def get_active_segment_path(self) -> Path:
        active_id = self.manifest["active_segment_id"]
        return self.segments_dir / f"segment_{active_id:06d}.jsonl"

    def write_event(self, event_data: dict):
        if not self.accepting:
            raise RuntimeError("Engine fermé.")
        self.queue.put(event_data)

    def _commit_loop(self):
        while not self._stop_event.is_set() or not self.queue.empty():
            batch = []
            start_time = time.time()
            
            while len(batch) < self.max_batch_size:
                timeout = self.max_batch_delay - (time.time() - start_time)
                if timeout <= 0:
                    break
                try:
                    item = self.queue.get(timeout=max(0.001, timeout))
                    batch.append(item)
                    self.queue.task_done()
                except queue.Empty:
                    break
            
            if not batch:
                continue

            try:
                batch_lines = [json.dumps(ev, ensure_ascii=False) + "\n" for ev in batch]
                batch_bytes = sum(len(line.encode("utf-8")) for line in batch_lines)
                
                active_path = self.get_active_segment_path()
                
                # Vérification de rotation par taille
                if active_path.exists() and (active_path.stat().st_size + batch_bytes) > self.max_segment_size:
                    # Rotation du segment actif vers SEALED
                    file_size = active_path.stat().st_size
                    sha = hashlib.sha256()
                    with open(active_path, "rb") as f:
                        while chunk := f.read(8192):
                            sha.update(chunk)
                    
                    self.manifest["segments"].append({
                        "id": self.manifest["active_segment_id"],
                        "file": active_path.name,
                        "size": file_size,
                        "state": "SEALED",
                        "sealed": True,
                        "sha256": sha.hexdigest()
                    })
                    
                    self.manifest["active_segment_id"] += 1
                    self._save_manifest_atomic()
                    active_path = self.get_active_segment_path()

                # Append atomique + fsync unique sur le segment actif
                with open(active_path, "a", encoding="utf-8") as f:
                    f.writelines(batch_lines)
                    f.flush()
                    os.fsync(f.fileno())

            except Exception as e:
                print(f"[ERREUR COMMIT] {e}")

    def close(self):
        self.accepting = False
        while not self.queue.empty():
            time.sleep(0.01)
        time.sleep(0.05)
        self._stop_event.set()
        self.commit_thread.join(timeout=3.0)
