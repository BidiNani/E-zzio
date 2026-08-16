import time
import json
import threading
from collections import deque
from pathlib import Path

class StabilizedMemoryActuatorV53:
    """
    Régulateur actif V5.3 avec Hystérésis anti-battement, Buffer Glissant 30s
    et Journalisation d'Audit Guardian.
    """
    def __init__(self, engine_ref, memory_engine_ref, state_dir: str = None, check_interval: float = 0.2):
        self.engine = engine_ref
        self.memory_engine = memory_engine_ref
        self.check_interval = check_interval
        
        self.base_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent
        self.audit_log_path = self.base_dir / "guardian_actuator_audit.jsonl"
        
        # Buffer Glissant sur 30 secondes (30s / 0.2s = 150 échantillons)
        self.history_buffer = deque(maxlen=150)
        
        # Paramètres d'Hystérésis
        self.hold_time_sec = 3.0  # Maintien minimal en mode de sécurité
        self.last_critical_time = 0.0
        self.current_regulation_tier = "NOMINAL"
        
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._actuator_loop, daemon=True)

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def _actuator_loop(self):
        while not self._stop_event.is_set():
            try:
                self.apply_regulation_tick()
            except Exception as e:
                print(f"[ACTUATOR V5.3 WARN] Erreur lors du tick : {e}", flush=True)
            time.sleep(self.check_interval)

    def _log_audit_event(self, event_type: str, prev_tier: str, new_tier: str, metrics: dict, reason: str):
        """Écrit un événement d'audit JSONL structuré pour le Guardian."""
        audit_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "transition": f"{prev_tier} -> {new_tier}",
            "reason": reason,
            "metrics": {
                "oom_index": metrics.get("oom_index"),
                "d_rss_dt_mbs": metrics.get("d_rss_dt_mbs"),
                "rss_mb": metrics.get("rss_mb"),
                "free_ram_gb": metrics.get("free_ram_gb")
            },
            "applied_params": {
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
                "max_batch_delay": getattr(self.engine, "max_batch_delay", 0.01)
            }
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
                f.flush()
        except Exception as e:
            print(f"[AUDIT LOG WARN] Échec écriture journal : {e}", flush=True)

    def apply_regulation_tick(self) -> dict:
        with self._lock:
            now = time.time()
            metrics = self.memory_engine.evaluate_state()
            oom_index = metrics.get("oom_index", 0.0)
            is_critical = metrics.get("critical_oom_risk", False)

            # Enregistrement dans le buffer glissant
            self.history_buffer.append({
                "timestamp": now,
                "oom_index": oom_index,
                "d_rss_dt_mbs": metrics.get("d_rss_dt_mbs", 0.0)
            })

            prev_tier = self.current_regulation_tier
            target_tier = prev_tier
            reason = "NOMINAL_STABLE"

            # 1. Évaluation de l'entrée en mode CRITICAL
            if is_critical or oom_index > 0.85:
                target_tier = "CRITICAL"
                self.last_critical_time = now
                reason = "CRITICAL_OOM_SPIKE_DETECTED"
            
            # 2. Application de l'Hystérésis pour la sortie de CRITICAL
            elif prev_tier == "CRITICAL":
                time_since_critical = now - self.last_critical_time
                if time_since_critical < self.hold_time_sec:
                    target_tier = "CRITICAL"  # Verrouillage Hold-Time
                    reason = f"HYSTERESIS_HOLD_TIME_ACTIVE ({self.hold_time_sec - time_since_critical:.1f}s remaining)"
                elif oom_index > 0.40:
                    target_tier = "MODERATE"  # Maintien modéré tant que l'indice reste > 0.40
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

            # Application des paramètres sur le moteur
            if target_tier == "CRITICAL":
                self.engine.max_batch_size = 250
                self.engine.max_batch_delay = 0.05
            elif target_tier == "MODERATE":
                self.engine.max_batch_size = 1000
                self.engine.max_batch_delay = 0.02
            else:
                self.engine.max_batch_size = 2000
                self.engine.max_batch_delay = 0.01

            self.current_regulation_tier = target_tier

            # Journalisation si changement de Tier
            if prev_tier != target_tier:
                print(f"[ACTUATOR V5.3] Transition : {prev_tier} -> {target_tier} | Raison : {reason}", flush=True)
                self._log_audit_event("TIER_TRANSITION", prev_tier, target_tier, metrics, reason)

            return {
                "tier": self.current_regulation_tier,
                "oom_index": oom_index,
                "reason": reason,
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
                "history_buffer_len": len(self.history_buffer)
            }

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
