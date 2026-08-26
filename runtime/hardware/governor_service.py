import os
import json
import time
import psutil
import threading
from pathlib import Path
from .cpu_topology import DynamicCPUTopology


class HardwareGovernorService:
    """
    Service de gouvernance matérielle 100% CPU/RAM (Ryzen 9 5900X).
    Gestion pure de l'affinité CCD0/CCD1, des priorités Win32 et du Heartbeat IPC.
    """

    def __init__(self, state_dir: str = None):
        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.ipc_state_file = self.base_dir / "state.json"
        self.topology = DynamicCPUTopology()
        self.process = psutil.Process(os.getpid())

        self.current_profile = "IDLE"
        self.evolution_allowed = False
        self._lock = threading.Lock()

        self._stop_heartbeat = threading.Event()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)

        self._update_ipc_state("INITIALIZING", self.topology.all_threads, "NORMAL")
        self.heartbeat_thread.start()

    def set_evolution_authorization(self, allowed: bool):
        with self._lock:
            self.evolution_allowed = allowed

    def _update_ipc_state(self, profile: str, affinity: list[int], priority: str):
        temp_ipc = self.ipc_state_file.with_suffix(".tmp")
        state_data = {
            "version": "5.0.0-CPU",
            "active_profile": profile,
            "heartbeat": time.time(),
            "alive": True,
            "pid": os.getpid(),
            "cpu_topology": {
                "total_logical": self.topology.total_logical,
                "total_physical": self.topology.total_physical,
                "is_ryzen_5900x": self.topology.is_ryzen_5900x,
                "assigned_affinity_count": len(affinity),
                "affinity_mask": affinity,
            },
            "win32_priority": priority,
            "evolution_allowed": self.evolution_allowed,
            "memory_rss_mb": round(self.process.memory_info().rss / (1024 * 1024), 2),
        }

        try:
            with open(temp_ipc, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_ipc, self.ipc_state_file)
        except Exception as e:
            print(f"[GOVERNOR IPC WARN] Erreur écriture état IPC : {e}", flush=True)

    def _heartbeat_loop(self):
        """Actualise le Heartbeat et la mémoire RSS toutes les 2 secondes."""
        while not self._stop_heartbeat.is_set():
            with self._lock:
                if self.ipc_state_file.exists():
                    try:
                        state = self.read_ipc_state()
                        if state:
                            state["heartbeat"] = time.time()
                            state["memory_rss_mb"] = round(self.process.memory_info().rss / (1024 * 1024), 2)
                            temp_ipc = self.ipc_state_file.with_suffix(".tmp")
                            with open(temp_ipc, "w", encoding="utf-8") as f:
                                json.dump(state, f, indent=2)
                                f.flush()
                                os.fsync(f.fileno())
                            os.replace(temp_ipc, self.ipc_state_file)
                    except Exception:
                        pass
            time.sleep(2.0)

    def set_profile(self, profile_name: str) -> dict:
        with self._lock:
            profile = profile_name.upper()

            if profile == "EVOLUTION" and not self.evolution_allowed:
                profile = "COMPUTE"

            if self.current_profile == profile:
                return self.read_ipc_state()

            affinity_mask = self.topology.get_mask_for_profile(profile)
            priority_str = "NORMAL"

            try:
                self.process.cpu_affinity(affinity_mask)

                if profile == "GAMING":
                    try:
                        self.process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        priority_str = "BELOW_NORMAL"
                    except Exception:
                        pass

                elif profile == "COMPUTE":
                    try:
                        self.process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
                        priority_str = "ABOVE_NORMAL"
                    except Exception:
                        pass

                elif profile == "EVOLUTION":
                    try:
                        self.process.nice(psutil.HIGH_PRIORITY_CLASS)
                        priority_str = "HIGH"
                    except Exception:
                        pass

                self.current_profile = profile
                self._update_ipc_state(profile, affinity_mask, priority_str)
                print(
                    f"[GOVERNOR CPU] Profil actif : {profile} | Affinity Threads : {len(affinity_mask)} | Priority : {priority_str}",
                    flush=True,
                )

            except Exception as e:
                print(f"[GOVERNOR ERROR] Échec changement de profil {profile} : {e}", flush=True)

            return self.read_ipc_state()

    def read_ipc_state(self) -> dict:
        if not self.ipc_state_file.exists():
            return {}
        try:
            with open(self.ipc_state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def stop(self):
        self._stop_heartbeat.set()
        if self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)
