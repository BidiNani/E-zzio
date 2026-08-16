import os
import json
import hashlib
import queue
import threading
import time
from pathlib import Path

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
        
        self.manifest = self._load_and_validate_manifest()
        
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
                    return data
            except Exception:
                pass
        return self._reconstruct_manifest_from_disk()

    def _reconstruct_manifest_from_disk(self) -> dict:
        segments_meta = []
        max_id = 0
        if self.segments_dir.exists():
            for p in sorted(self.segments_dir.glob("segment_*.jsonl")):
                try:
                    seg_id = int(p.stem.split("_")[1])
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
        new_manifest = {
            "active_segment_id": active_id,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": segments_meta
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
            for index, raw_line in enumerate(raw.split(b"\n")):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    decoded = stripped.decode("utf-8")
                    json.loads(decoded)
                    valid_lines.append(decoded)
                except Exception:
                    if index == len(raw.split(b"\n")) - 1:
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
        temp_manifest = self.manifest_path.with_suffix(".json.tmp")
        temp_sha = self.manifest_sha_path.with_suffix(".sha256.tmp")
        manifest_data = json.dumps(self.manifest, indent=2)
        
        with open(temp_manifest, "w", encoding="utf-8") as f:
            f.write(manifest_data)
            f.flush()
            os.fsync(f.fileno())

        sha = hashlib.sha256()
        sha.update(manifest_data.encode("utf-8"))
        
        with open(temp_sha, "w", encoding="utf-8") as f:
            f.write(sha.hexdigest())
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_manifest, self.manifest_path)
        os.replace(temp_sha, self.manifest_sha_path)

    def get_active_segment_path(self) -> Path:
        return self.segments_dir / f"segment_{self.manifest['active_segment_id']:06d}.jsonl"

    def write_event(self, event_data: dict):
        if not self.accepting:
            raise RuntimeError("Engine fermé.")
        # Injecte l'horodatage d'entrée dans la queue pour le profilage de latence
        event_data["_queued_at"] = time.time()
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
                    # Horodatage effectif de sortie de queue / début de commit
                    item["_committed_at"] = time.time()
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
                
                if active_path.exists() and (active_path.stat().st_size + batch_bytes) > self.max_segment_size:
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

                with open(active_path, "a", encoding="utf-8") as f:
                    f.writelines(batch_lines)
                    f.flush()
                    os.fsync(f.fileno())

            except Exception:
                pass

    def close(self):
        self.accepting = False
        while not self.queue.empty():
            time.sleep(0.01)
        time.sleep(0.05)
        self._stop_event.set()
        self.commit_thread.join(timeout=3.0)
