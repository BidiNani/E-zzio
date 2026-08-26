import os
import time
import json
import threading
from collections import deque
from pathlib import Path


class PersistentMemoryActuatorV54:
    """
    Régulateur actif V5.4 d'infrastructure.
    Gère la persistance d'état sur disque, le couplage direct avec le moteur
    de stockage réel, la détection d'anomalies de fréquence et l'audit Guardian.
    """

    def __init__(self, engine_ref, memory_engine_ref, state_dir: str = None, check_interval: float = 0.2):
        self.engine = engine_ref
        self.memory_engine = memory_engine_ref
        self.check_interval = check_interval

        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.state_dir = self.base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file_path = self.state_dir / "memory_actuator_state.json"
        self.audit_log_path = self.base_dir / "guardian_actuator_audit.jsonl"

        # Buffer glissant 30s pour lissage (150 échantillons à 0.2s)
        self.history_buffer = deque(maxlen=150)

        # Historique d'anomalies (fenêtre glissante d'1h / 3600s)
        self.critical_spikes_window = deque()
        self.max_spikes_per_hour = 10
        self.anomaly_active = False

        # Paramètres d'Hystérésis
        self.hold_time_sec = 3.0
        self.last_critical_time = 0.0
        self.current_regulation_tier = "NOMINAL"

        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Chargement de l'état précédent si disponible
        self._load_persisted_state()

        self.monitor_thread = threading.Thread(target=self._actuator_loop, daemon=True)

    def _load_persisted_state(self):
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_regulation_tier = data.get("current_regulation_tier", "NOMINAL")
                    self.last_critical_time = data.get("last_critical_time", 0.0)
                    self.anomaly_active = data.get("anomaly_active", False)
                    print(
                        f"[ACTUATOR STATE LOADED] Tier restauré : {self.current_regulation_tier} | Anomaly Flag : {self.anomaly_active}",
                        flush=True,
                    )
            except Exception as e:
                print(f"[ACTUATOR STATE WARN] Impossible de lire l'état persistant : {e}", flush=True)

    def _save_persisted_state_atomic(self):
        temp_path = self.state_file_path.with_suffix(".tmp")
        state_data = {
            "version": "5.4.0",
            "timestamp": time.time(),
            "current_regulation_tier": self.current_regulation_tier,
            "last_critical_time": self.last_critical_time,
            "anomaly_active": self.anomaly_active,
            "spikes_last_hour_count": len(self.critical_spikes_window),
        }
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.state_file_path)
        except Exception as e:
            print(f"[ACTUATOR STATE WARN] Erreur écriture état persistant : {e}", flush=True)

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def _actuator_loop(self):
        while not self._stop_event.is_set():
            try:
                self.apply_regulation_tick()
            except Exception as e:
                print(f"[ACTUATOR V5.4 WARN] Erreur tick : {e}", flush=True)
            time.sleep(self.check_interval)

    def _log_audit_event(self, event_type: str, prev_tier: str, new_tier: str, metrics: dict, reason: str):
        audit_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "transition": f"{prev_tier} -> {new_tier}",
            "reason": reason,
            "anomaly_active": self.anomaly_active,
            "metrics": {
                "oom_index": metrics.get("oom_index"),
                "d_rss_dt_mbs": metrics.get("d_rss_dt_mbs"),
                "rss_mb": metrics.get("rss_mb"),
                "free_ram_gb": metrics.get("free_ram_gb"),
            },
            "applied_params": {
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
                "max_batch_delay": getattr(self.engine, "max_batch_delay", 0.01),
            },
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
                f.flush()
        except Exception as e:
            print(f"[AUDIT LOG WARN] Échec journalisation : {e}", flush=True)

    def apply_regulation_tick(self) -> dict:
        with self._lock:
            now = time.time()
            metrics = self.memory_engine.evaluate_state()
            oom_index = metrics.get("oom_index", 0.0)
            is_critical = metrics.get("critical_oom_risk", False)

            # Nettoyage de la fenêtre d'anomalies (> 3600s)
            while self.critical_spikes_window and (now - self.critical_spikes_window[0]) > 3600.0:
                self.critical_spikes_window.popleft()

            self.history_buffer.append({"timestamp": now, "oom_index": oom_index})

            prev_tier = self.current_regulation_tier
            target_tier = prev_tier
            reason = "NOMINAL_STABLE"

            # 1. Évaluation d'entrée en CRITICAL
            if is_critical or oom_index > 0.85:
                target_tier = "CRITICAL"
                if prev_tier != "CRITICAL":
                    self.critical_spikes_window.append(now)
                    # Vérification du seuil d'anomalie
                    if len(self.critical_spikes_window) > self.max_spikes_per_hour:
                        self.anomaly_active = True
                        reason = f"ANOMALY_FREQUENT_OOM_SPIKES ({len(self.critical_spikes_window)} spikes/h)"
                    else:
                        reason = "CRITICAL_OOM_SPIKE_DETECTED"
                self.last_critical_time = now

            # 2. Hystérésis de sortie de CRITICAL
            elif prev_tier == "CRITICAL":
                time_since_critical = now - self.last_critical_time
                if time_since_critical < self.hold_time_sec:
                    target_tier = "CRITICAL"
                    reason = f"HYSTERESIS_HOLD_TIME_ACTIVE ({self.hold_time_sec - time_since_critical:.1f}s remaining)"
                elif oom_index > 0.40:
                    target_tier = "MODERATE"
                    reason = "HYSTERESIS_HIGH_WATERMARK_MODERATE"
                else:
                    target_tier = "NOMINAL"
                    reason = "MEMORY_RECOVERY_CERTIFIED"

            # 3. Mode intermédiaire
            elif oom_index > 0.60:
                target_tier = "MODERATE"
                reason = "RAM_PRESSURE_MODERATE"
            else:
                target_tier = "NOMINAL"
                reason = "MEMORY_NOMINAL"

            # Application des paramètres de bridage sur le moteur
            # Si une anomalie est active, on plafonne le mode NOMINAL à MODERATE (1000 items max)
            if target_tier == "CRITICAL":
                self.engine.max_batch_size = 250
                self.engine.max_batch_delay = 0.05
            elif target_tier == "MODERATE" or self.anomaly_active:
                self.engine.max_batch_size = 1000
                self.engine.max_batch_delay = 0.02
            else:
                self.engine.max_batch_size = 2000
                self.engine.max_batch_delay = 0.01

            self.current_regulation_tier = target_tier

            # Sauvegarde atomique de l'état et journalisation
            if prev_tier != target_tier or self.anomaly_active:
                self._save_persisted_state_atomic()

            if prev_tier != target_tier:
                print(f"[ACTUATOR V5.4] Transition : {prev_tier} -> {target_tier} | Raison : {reason}", flush=True)
                self._log_audit_event("TIER_TRANSITION", prev_tier, target_tier, metrics, reason)

            return {
                "tier": self.current_regulation_tier,
                "oom_index": oom_index,
                "reason": reason,
                "anomaly_active": self.anomaly_active,
                "spikes_last_hour": len(self.critical_spikes_window),
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
            }

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
