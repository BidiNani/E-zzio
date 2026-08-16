import os
import sys
import json
import hashlib
import queue
import threading
import time
from pathlib import Path

class FaultInjector:
    def __init__(self, active_hook: str = None):
        self.active_hook = active_hook

    def trigger(self, hook_name: str):
        if self.active_hook == hook_name:
            print(f"[CHAOS INJECTOR] FAULT TRIGGERED: '{hook_name}' -> Terminaison brutale (os._exit(137))...", flush=True)
            os._exit(137)

class ConcurrentSegmentedEngine:
    def __init__(self, store_root: str, max_segment_size: int = 5 * 1024 * 1024, max_batch_size: int = 1000, max_batch_delay: float = 0.02, fault_injector: FaultInjector = None):
        self.store_root = Path(store_root)
        self.segments_dir = self.store_root / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_root / "manifest.json"
        self.manifest_sha_path = self.store_root / "manifest.json.sha256"
        self.max_segment_size = max_segment_size
        
        self.max_batch_size = max_batch_size
        self.max_batch_delay = max_batch_delay
        self.fault_injector = fault_injector or FaultInjector()
        
        self.queue = queue.Queue(maxsize=50000)
        self._stop_event = threading.Event()
        self.accepting = True
        self._fatal_error = None
        
        self._purge_orphaned_temps()
        self.manifest = self._load_and_validate_manifest()
        
        self.commit_thread = threading.Thread(target=self._commit_loop, daemon=True)
        self.commit_thread.start()

    def _purge_orphaned_temps(self):
        for tmp_file in self.store_root.glob("*.tmp"):
            try:
                tmp_file.unlink()
            except Exception:
                pass

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
                    manifest_seg_files = {s["file"] for s in data.get("segments", [])}
                    if active_seg_id := data.get("active_segment_id"):
                        manifest_seg_files.add(f"segment_{active_seg_id:06d}.jsonl")
                    
                    physical_seg_files = {p.name for p in self.segments_dir.glob("segment_*.jsonl")}
                    if not physical_seg_files.issubset(manifest_seg_files):
                        return self._reconstruct_manifest_from_disk()
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

        active_id = max_id if max_id > 0 else 1
        closed_segments = []
        
        if segments_meta:
            last_seg = segments_meta.pop()
            active_id = last_seg["id"]
            closed_segments = segments_meta

        new_manifest = {
            "active_segment_id": active_id,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": closed_segments
        }
        
        self.manifest = new_manifest
        self._save_manifest_atomic()
        return new_manifest

    def seal_active_segment(self):
        active_path = self.get_active_segment_path()
        if not active_path.exists():
            return

        sha = hashlib.sha256()
        with open(active_path, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)

        self.manifest["segments"].append({
            "id": self.manifest["active_segment_id"],
            "file": active_path.name,
            "size": active_path.stat().st_size,
            "state": "SEALED",
            "sealed": True,
            "sha256": sha.hexdigest()
        })

        self.manifest["active_segment_id"] += 1
        self._save_manifest_atomic()

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

        self.fault_injector.trigger("PRE_MANIFEST_SWAP")

        os.replace(temp_manifest, self.manifest_path)
        os.replace(temp_sha, self.manifest_sha_path)

    def get_active_segment_path(self) -> Path:
        return self.segments_dir / f"segment_{self.manifest['active_segment_id']:06d}.jsonl"

    def write_event(self, event_data: dict):
        if not self.accepting or self._fatal_error:
            raise RuntimeError(f"Engine indisponible: {self._fatal_error}")
        self.queue.put(event_data)

    def _commit_loop(self):
        try:
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
                    except queue.Empty:
                        break
                
                if not batch:
                    continue

                batch_lines = [json.dumps(ev, ensure_ascii=False) + "\n" for ev in batch]
                batch_bytes = sum(len(line.encode("utf-8")) for line in batch_lines)
                active_path = self.get_active_segment_path()
                
                if active_path.exists() and (active_path.stat().st_size + batch_bytes) > self.max_segment_size:
                    self.seal_active_segment()
                    active_path = self.get_active_segment_path()

                self.fault_injector.trigger("PRE_WRITE")

                with open(active_path, "a", encoding="utf-8") as f:
                    f.writelines(batch_lines)
                    f.flush()
                    self.fault_injector.trigger("PRE_FSYNC")
                    os.fsync(f.fileno())

                self.fault_injector.trigger("PRE_TASK_DONE")

                for _ in batch:
                    self.queue.task_done()
        except Exception as e:
            self._fatal_error = e
            self._stop_event.set()
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except Exception:
                    break
            raise

    def close(self):
        self.accepting = False
        while self.commit_thread.is_alive() and not self._fatal_error and not self.queue.empty():
            time.sleep(0.01)

        if self._fatal_error:
            raise RuntimeError(f"Engine fatal error: {self._fatal_error}")

        self.queue.join()
        self._stop_event.set()
        if self.commit_thread.is_alive():
            self.commit_thread.join(timeout=2.0)
