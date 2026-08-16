import os
import sys
import json
import hashlib
import queue
import threading
import time
import psutil
from collections import defaultdict
from pathlib import Path

class RyzenHardwareGovernor:
    """
    Gouverneur matériel E-ZZIO dédié au Ryzen 9 5900X (12C / 24T sur 2 CCDs).
    Ajuste l'affinité CPU (CCD0/CCD1) et les priorités du processus Win32 à chaud.
    """
    def __init__(self, engine_ref):
        self.engine = engine_ref
        self.process = psutil.Process(os.getpid())
        
        # Masques d'affinité Ryzen 5900X
        self.ccd0_mask = list(range(0, 12))      # CCD0 : Threads 0 à 11 (Cœurs 0-5)
        self.ccd1_mask = list(range(12, 24))     # CCD1 : Threads 12 à 23 (Cœurs 6-11)
        self.compute_mask = list(range(2, 24))   # CCD0+CCD1 en préservant T0-T1 (Kernel OS)
        self.all_cores_mask = list(range(0, 24)) # 24 threads débridés
        
        self.current_profile = None
        self._lock = threading.Lock()

    def apply_profile(self, profile_name: str) -> dict:
        with self._lock:
            profile_name = profile_name.upper()
            if self.current_profile == profile_name:
                return self.get_telemetry()

            applied_affinity = []
            applied_priority = "NORMAL"

            try:
                if profile_name == "GAMING":
                    # Isole E-ZZIO sur le CCD1 (Threads 12-23) pour libérer le CCD0 aux jeux/OS
                    applied_affinity = self.ccd1_mask
                    self.process.cpu_affinity(applied_affinity)
                    try:
                        self.process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        applied_priority = "BELOW_NORMAL"
                    except Exception:
                        pass
                    self.engine.max_batch_size = 1000

                elif profile_name == "COMPUTE":
                    # CCD0 + CCD1 (Threads 2-23) en préservant T0-T1
                    applied_affinity = self.compute_mask
                    self.process.cpu_affinity(applied_affinity)
                    try:
                        self.process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
                        applied_priority = "ABOVE_NORMAL"
                    except Exception:
                        pass
                    self.engine.max_batch_size = 2000

                elif profile_name == "EVOLUTION":
                    # Débridage total sur les 24 threads
                    applied_affinity = self.all_cores_mask
                    self.process.cpu_affinity(applied_affinity)
                    try:
                        self.process.nice(psutil.HIGH_PRIORITY_CLASS)
                        applied_priority = "HIGH"
                    except Exception:
                        pass
                    self.engine.max_batch_size = 4000

                else:
                    raise ValueError(f"Profil inconnu : {profile_name}")

                self.current_profile = profile_name
                print(f"[GOVERNOR] Profil actif : {profile_name} | Affinité : {len(applied_affinity)} threads | Priorité : {applied_priority}", flush=True)

            except Exception as e:
                print(f"[GOVERNOR WARN] Erreur lors de l'application du profil {profile_name} : {e}", flush=True)

            return self.get_telemetry()

    def get_telemetry(self) -> dict:
        try:
            curr_affinity = self.process.cpu_affinity()
        except Exception:
            curr_affinity = []

        return {
            "profile": self.current_profile,
            "assigned_threads_count": len(curr_affinity),
            "cpu_affinity_mask": curr_affinity,
            "process_rss_mb": round(self.process.memory_info().rss / (1024 * 1024), 2),
            "process_cpu_percent": self.process.cpu_percent(interval=None)
        }

class L1MemoryIndex:
    def __init__(self):
        self._lock = threading.Lock()
        self.by_agent = defaultdict(list)
        self.by_type = defaultdict(list)
        self.event_count = 0

    def index_event(self, event: dict):
        evt_id = event.get("event_id")
        agent = event.get("agent_source")
        stype = event.get("semantic_type")
        
        with self._lock:
            if agent:
                self.by_agent[agent].append(evt_id)
            if stype:
                self.by_type[stype].append(evt_id)
            self.event_count += 1

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_indexed_l1": self.event_count,
                "agents_count": len(self.by_agent),
                "types_count": len(self.by_type)
            }

class ConcurrentSegmentedEngineV48:
    def __init__(self, store_root: str, max_segment_size: int = 50 * 1024 * 1024, max_batch_size: int = 2000, max_batch_delay: float = 0.02):
        self.store_root = Path(store_root)
        self.segments_dir = self.store_root / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_root / "manifest.json"
        self.manifest_sha_path = self.store_root / "manifest.json.sha256"
        self.max_segment_size = max_segment_size
        
        self.max_batch_size = max_batch_size
        self.max_batch_delay = max_batch_delay
        
        self.l1_index = L1MemoryIndex()
        self.governor = RyzenHardwareGovernor(self)
        
        self.queue = queue.Queue(maxsize=150000)
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
        sealed_segments = []
        active_candidates = []
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

                is_sealed = self._inspect_segment_footer(p)

                sha = hashlib.sha256()
                with open(p, "rb") as f:
                    while chunk := f.read(8192):
                        sha.update(chunk)

                if is_sealed:
                    sealed_segments.append({
                        "id": seg_id,
                        "file": p.name,
                        "size": file_size,
                        "state": "SEALED",
                        "sealed": True,
                        "sha256": sha.hexdigest()
                    })
                else:
                    active_candidates.append(seg_id)

        active_id = max(active_candidates) if active_candidates else (max_id + 1 if max_id > 0 else 1)

        new_manifest = {
            "active_segment_id": active_id,
            "max_segment_size_bytes": self.max_segment_size,
            "segments": sealed_segments
        }
        
        self.manifest = new_manifest
        self._save_manifest_atomic()
        return new_manifest

    def _inspect_segment_footer(self, file_path: Path) -> bool:
        try:
            with open(file_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size == 0:
                    return False
                f.seek(max(0, size - 2048))
                lines = f.read().split(b"\n")
                for raw_line in reversed(lines):
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped.decode("utf-8"))
                        if isinstance(data, dict) and data.get("__type__") == "SEGMENT_FOOTER":
                            return True
                    except Exception:
                        pass
                    break
        except Exception:
            pass
        return False

    def seal_active_segment(self):
        active_path = self.get_active_segment_path()
        if not active_path.exists():
            return

        seg_id = self.manifest["active_segment_id"]
        sha = hashlib.sha256()
        with open(active_path, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)

        footer_obj = {
            "__type__": "SEGMENT_FOOTER",
            "segment_id": seg_id,
            "state": "SEALED",
            "timestamp": time.time(),
            "payload_sha256_pre_footer": sha.hexdigest()
        }
        footer_line = json.dumps(footer_obj, ensure_ascii=False) + "\n"
        
        with open(active_path, "a", encoding="utf-8") as f:
            f.write(footer_line)
            f.flush()
            os.fsync(f.fileno())

        final_sha = hashlib.sha256()
        with open(active_path, "rb") as f:
            while chunk := f.read(8192):
                final_sha.update(chunk)

        self.manifest["segments"].append({
            "id": seg_id,
            "file": active_path.name,
            "size": active_path.stat().st_size,
            "state": "SEALED",
            "sealed": True,
            "sha256": final_sha.hexdigest()
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

        os.replace(temp_manifest, self.manifest_path)
        os.replace(temp_sha, self.manifest_sha_path)

    def get_active_segment_path(self) -> Path:
        return self.segments_dir / f"segment_{self.manifest['active_segment_id']:06d}.jsonl"

    def write_event(self, event_data: dict):
        if not self.accepting or self._fatal_error:
            raise RuntimeError(f"Engine indisponible: {self._fatal_error}")
        self.l1_index.index_event(event_data)
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

                with open(active_path, "a", encoding="utf-8") as f:
                    f.writelines(batch_lines)
                    f.flush()
                    os.fsync(f.fileno())

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
