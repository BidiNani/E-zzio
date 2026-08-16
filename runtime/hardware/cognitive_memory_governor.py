import os
import time
import json
import threading
from collections import deque
from pathlib import Path

class GuardianCognitiveGovernorV56:
    """
    Régulateur mémoire cognitif V5.6.
    Intègre :
    - Calcul du temps avant saturation (T_ttc)
    - Auto-ajustement dynamique des seuils (Dynamic Threshold Tuning) basés sur l'historique 24h
    - Persistance atomique d'état et mémoire cognitive d'incidents
    - Thread d'arrière-plan d'actuation réactive
    """
    WORKLOAD_PROFILES = {
        "INGESTION_BURST": {"base_oom_threshold": 0.80, "hold_time": 4.0, "max_batch": 3000},
        "FULL_INDEXING":  {"base_oom_threshold": 0.70, "hold_time": 5.0, "max_batch": 1500},
        "GUARDIAN_SCAN":  {"base_oom_threshold": 0.85, "hold_time": 2.0, "max_batch": 2000},
        "IDLE_MAINTENANCE":{"base_oom_threshold": 0.90, "hold_time": 1.0, "max_batch": 4000}
    }

    def __init__(self, engine_ref, memory_engine_ref, state_dir: str = None, check_interval: float = 0.2):
        self.engine = engine_ref
        self.memory_engine = memory_engine_ref
        self.check_interval = check_interval
        
        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.state_dir = self.base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file_path = self.state_dir / "cognitive_v56_state.json"
        self.audit_log_path = self.base_dir / "guardian_actuator_audit.jsonl"
        
        self.active_workload = "INGESTION_BURST"
        self.history_buffer = deque(maxlen=150)
        self.spikes_24h_history = deque()
        
        # Métriques cognitives
        self.total_preemptive_throttles = 0
        self.ttc_trigger_history = deque(maxlen=50)
        self.last_critical_time = 0.0
        self.current_regulation_tier = "NOMINAL"
        
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        self._load_cognitive_state()
        self.monitor_thread = threading.Thread(target=self._actuator_loop, daemon=True)

    def _load_cognitive_state(self):
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_workload = data.get("active_workload", "INGESTION_BURST")
                    self.current_regulation_tier = data.get("current_regulation_tier", "NOMINAL")
                    self.total_preemptive_throttles = data.get("total_preemptive_throttles", 0)
                    spikes = data.get("spikes_24h_history", [])
                    now = time.time()
                    self.spikes_24h_history = deque([s for s in spikes if (now - s) <= 86400.0])
                    print(f"[COGNITIVE STATE LOADED] Workload: {self.active_workload} | Spikes 24h: {len(self.spikes_24h_history)}", flush=True)
            except Exception as e:
                print(f"[COGNITIVE STATE WARN] Échec lecture état : {e}", flush=True)

    def _save_cognitive_state_atomic(self):
        temp_path = self.state_file_path.with_suffix(".tmp")
        state_data = {
            "version": "5.6.0",
            "timestamp": time.time(),
            "active_workload": self.active_workload,
            "current_regulation_tier": self.current_regulation_tier,
            "total_preemptive_throttles": self.total_preemptive_throttles,
            "effective_threshold": self.calculate_effective_threshold(),
            "spikes_24h_count": len(self.spikes_24h_history),
            "spikes_24h_history": list(self.spikes_24h_history)
        }
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.state_file_path)
        except Exception as e:
            print(f"[COGNITIVE STATE WARN] Erreur écriture atomique : {e}", flush=True)

    def _actuator_loop(self):
        while not self._stop_event.set_is_set() if hasattr(self._stop_event, 'set_is_set') else not self._stop_event.is_set():
            try:
                self.apply_regulation_tick()
            except Exception as e:
                print(f"[COGNITIVE GOVERNOR WARN] Erreur tick : {e}", flush=True)
            time.sleep(self.check_interval)

    def set_workload_context(self, workload_name: str):
        with self._lock:
            workload_name = workload_name.upper()
            if workload_name in self.WORKLOAD_PROFILES:
                self.active_workload = workload_name
                print(f"[COGNITIVE V5.6] Profil contextuel actif : {workload_name}", flush=True)

    def calculate_effective_threshold(self) -> float:
        """
        Auto-ajustement dynamique du seuil (Dynamic Threshold Tuning) :
        Abaisse le seuil de base jusqu'à -0.10 selon la fréquence de spikes sur 24h.
        """
        base_thresh = self.WORKLOAD_PROFILES[self.active_workload]["base_oom_threshold"]
        now = time.time()
        
        # Purge des événements > 24h (86400s)
        while self.spikes_24h_history and (now - self.spikes_24h_history[0]) > 86400.0:
            self.spikes_24h_history.popleft()
            
        penalty = min(0.10, (len(self.spikes_24h_history) / 10.0) * 0.10)
        return round(max(0.50, base_thresh - penalty), 3)

    def calculate_time_to_critical(self, current_rss_mb: float, d_rss_dt: float) -> float:
        budget_mb = getattr(self.memory_engine, "budget_mb", 10240.0)
        remaining_mb = max(0.0, budget_mb - current_rss_mb)
        if d_rss_dt <= 0.1:
            return 999.0
        return remaining_mb / d_rss_dt

    def apply_regulation_tick(self) -> dict:
        with self._lock:
            now = time.time()
            metrics = self.memory_engine.evaluate_state()
            oom_index = metrics.get("oom_index", 0.0)
            d_rss_dt = metrics.get("d_rss_dt_mbs", 0.0)
            rss_mb = metrics.get("rss_mb", 0.0)
            
            t_ttc = self.calculate_time_to_critical(rss_mb, d_rss_dt)
            profile_cfg = self.WORKLOAD_PROFILES[self.active_workload]
            effective_threshold = self.calculate_effective_threshold()
            
            prev_tier = self.current_regulation_tier
            target_tier = prev_tier
            reason = "NOMINAL_COGNITIVE_STABLE"

            # 1. Déclenchement Prédictif ou par Seuil Auto-Ajusté
            if t_ttc <= 8.0 or oom_index > effective_threshold:
                target_tier = "CRITICAL"
                if prev_tier != "CRITICAL":
                    self.spikes_24h_history.append(now)
                    self.total_preemptive_throttles += 1
                    self.ttc_trigger_history.append(t_ttc)
                self.last_critical_time = now
                reason = f"COGNITIVE_PREEMPTIVE_THROTTLE (T_ttc={t_ttc:.1f}s, OOM={oom_index:.2f}, Threshold={effective_threshold})"

            # 2. Hystérésis contextuel
            elif prev_tier == "CRITICAL":
                time_since_critical = now - self.last_critical_time
                if time_since_critical < profile_cfg["hold_time"]:
                    target_tier = "CRITICAL"
                    reason = f"HYSTERESIS_HOLD_TIME ({profile_cfg['hold_time'] - time_since_critical:.1f}s remaining)"
                elif oom_index > (effective_threshold * 0.6):
                    target_tier = "MODERATE"
                    reason = "HIGH_WATERMARK_MODERATE"
                else:
                    target_tier = "NOMINAL"
                    reason = "COGNITIVE_RECOVERY_CERTIFIED"

            elif oom_index > (effective_threshold * 0.75):
                target_tier = "MODERATE"
                reason = "RAM_PRESSURE_MODERATE"
            else:
                target_tier = "NOMINAL"

            # Application dynamique des paramètres au moteur
            if target_tier == "CRITICAL":
                self.engine.max_batch_size = 250
                self.engine.max_batch_delay = 0.05
            elif target_tier == "MODERATE":
                self.engine.max_batch_size = int(profile_cfg["max_batch"] * 0.5)
                self.engine.max_batch_delay = 0.02
            else:
                self.engine.max_batch_size = profile_cfg["max_batch"]
                self.engine.max_batch_delay = 0.01

            self.current_regulation_tier = target_tier
            
            if prev_tier != target_tier or target_tier == "CRITICAL":
                self._save_cognitive_state_atomic()

            return {
                "tier": target_tier,
                "workload_context": self.active_workload,
                "effective_threshold": effective_threshold,
                "t_ttc_seconds": round(t_ttc, 2),
                "oom_index": oom_index,
                "spikes_24h_count": len(self.spikes_24h_history),
                "total_throttles": self.total_preemptive_throttles,
                "reason": reason,
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000)
            }

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
