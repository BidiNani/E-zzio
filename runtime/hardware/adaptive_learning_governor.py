import time
import threading
from collections import deque
from pathlib import Path


class AdaptiveLearningGovernorV55:
    """
    Régulateur mémoire adaptatif et prédictif V5.5.
    Intègre l'estimation préventive du temps avant saturation (T_ttc)
    et la modulation des seuils selon le profil de charge actif.
    """

    WORKLOAD_PROFILES = {
        "INGESTION_BURST": {"oom_threshold": 0.80, "hold_time": 4.0, "max_batch": 3000},
        "FULL_INDEXING": {"oom_threshold": 0.70, "hold_time": 5.0, "max_batch": 1500},
        "GUARDIAN_SCAN": {"oom_threshold": 0.85, "hold_time": 2.0, "max_batch": 2000},
        "IDLE_MAINTENANCE": {"oom_threshold": 0.90, "hold_time": 1.0, "max_batch": 4000},
    }

    def __init__(self, engine_ref, memory_engine_ref, state_dir: str = None, check_interval: float = 0.2):
        self.engine = engine_ref
        self.memory_engine = memory_engine_ref
        self.check_interval = check_interval

        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.state_dir = self.base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file_path = self.state_dir / "adaptive_v55_state.json"

        self.active_workload = "INGESTION_BURST"
        self.history_buffer = deque(maxlen=150)
        self.last_critical_time = 0.0
        self.current_regulation_tier = "NOMINAL"

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._actuator_loop, daemon=True)

    def _actuator_loop(self):
        """Boucle d'arrière-plan exécutant les régulations périodiques."""
        while not self._stop_event.is_set():
            try:
                self.apply_regulation_tick()
            except Exception as e:
                print(f"[GOVERNOR V5.5 WARN] Erreur lors du tick : {e}", flush=True)
            time.sleep(self.check_interval)

    def set_workload_context(self, workload_name: str):
        with self._lock:
            workload_name = workload_name.upper()
            if workload_name in self.WORKLOAD_PROFILES:
                self.active_workload = workload_name
                print(f"[GOVERNOR V5.5] Context Workload basculé sur : {workload_name}", flush=True)

    def calculate_time_to_critical(self, current_rss_mb: float, d_rss_dt: float) -> float:
        """Calcul du temps théorique restant (en secondes) avant saturation du budget."""
        budget_mb = getattr(self.memory_engine, "budget_mb", 10240.0)
        remaining_mb = max(0.0, budget_mb - current_rss_mb)
        if d_rss_dt <= 0.1:
            return 999.0  # Stable ou décroissance
        return remaining_mb / d_rss_dt

    def apply_regulation_tick(self) -> dict:
        with self._lock:
            now = time.time()
            metrics = self.memory_engine.evaluate_state()
            oom_index = metrics.get("oom_index", 0.0)
            d_rss_dt = metrics.get("d_rss_dt_mbs", 0.0)
            rss_mb = metrics.get("rss_mb", 0.0)

            # Calcul du T_ttc
            t_ttc = self.calculate_time_to_critical(rss_mb, d_rss_dt)
            profile_cfg = self.WORKLOAD_PROFILES[self.active_workload]

            prev_tier = self.current_regulation_tier
            target_tier = prev_tier
            reason = "NOMINAL_PREDICTIVE_STABLE"

            # 1. Éléments Déclencheurs Prédictifs (T_ttc <= 8s OU seuil de profil dépassé)
            if t_ttc <= 8.0 or oom_index > profile_cfg["oom_threshold"]:
                target_tier = "CRITICAL"
                self.last_critical_time = now
                reason = f"PREDICTIVE_PREEMPTIVE_THROTTLE (T_ttc={t_ttc:.1f}s, OOM={oom_index:.2f})"

            # 2. Hystérésis contextuel de sortie
            elif prev_tier == "CRITICAL":
                time_since_critical = now - self.last_critical_time
                if time_since_critical < profile_cfg["hold_time"]:
                    target_tier = "CRITICAL"
                    reason = f"HYSTERESIS_HOLD_TIME ({profile_cfg['hold_time'] - time_since_critical:.1f}s)"
                elif oom_index > (profile_cfg["oom_threshold"] * 0.6):
                    target_tier = "MODERATE"
                    reason = "HIGH_WATERMARK_MODERATE"
                else:
                    target_tier = "NOMINAL"
                    reason = "PREDICTIVE_RECOVERY_CERTIFIED"

            elif oom_index > (profile_cfg["oom_threshold"] * 0.75):
                target_tier = "MODERATE"
                reason = "RAM_PRESSURE_MODERATE"
            else:
                target_tier = "NOMINAL"

            # Application des paramètres dynamiques au moteur
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
            return {
                "tier": target_tier,
                "workload_context": self.active_workload,
                "t_ttc_seconds": round(t_ttc, 2),
                "oom_index": oom_index,
                "reason": reason,
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
            }

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
