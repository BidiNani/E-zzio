import time
import threading
from typing import Dict, Any

class SemanticBackpressureController:
    """
    Contrôleur de backpressure V6.0.
    Raccorde le Governor Cognitif V5.6 aux pipelines sémantiques.
    """
    def __init__(self, governor_ref, check_interval: float = 0.05):
        self.governor = governor_ref
        self.check_interval = check_interval
        
        self.context_window_map = {
            "NOMINAL": 16384,
            "MODERATE": 8192,
            "CRITICAL": 2048
        }
        
        self._lock = threading.Lock()
        self.current_state: Dict[str, Any] = {}
        
        self._stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._controller_loop, daemon=True)
        self.update_backpressure_state()

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def _controller_loop(self):
        while not self._stop_event.is_set():
            try:
                self.update_backpressure_state()
            except Exception as e:
                print(f"[BACKPRESSURE V6.0 WARN] Erreur lors de l'actualisation : {e}", flush=True)
            time.sleep(self.check_interval)

    def update_backpressure_state(self) -> Dict[str, Any]:
        with self._lock:
            gov_tick = self.governor.apply_regulation_tick()
            tier = gov_tick.get("tier", "NOMINAL")
            t_ttc = gov_tick.get("t_ttc_seconds", 999.0)
            oom_index = gov_tick.get("oom_index", 0.0)

            allocated_n_ctx = self.context_window_map.get(tier, 2048)
            allow_background_agents = (tier == "NOMINAL")
            ingestion_paused = (tier == "CRITICAL")

            self.current_state = {
                "timestamp": time.time(),
                "regulation_tier": tier,
                "oom_index": oom_index,
                "t_ttc_seconds": t_ttc,
                "llm_allocated_n_ctx": allocated_n_ctx,
                "allow_background_agents": allow_background_agents,
                "ingestion_paused": ingestion_paused,
                "max_batch_size": gov_tick.get("max_batch_size", 2000),
                "reason": gov_tick.get("reason", "NOMINAL")
            }
            return self.current_state

    def get_llm_context_budget(self) -> int:
        with self._lock:
            return self.current_state.get("llm_allocated_n_ctx", 4096)

    def is_agent_execution_allowed(self, is_background_agent: bool = True) -> bool:
        with self._lock:
            if not is_background_agent:
                return True
            return self.current_state.get("allow_background_agents", False)

    def acquire_ingestion_slot(self) -> float:
        with self._lock:
            tier = self.current_state.get("regulation_tier", "NOMINAL")
            if tier == "CRITICAL":
                return 0.05
            elif tier == "MODERATE":
                return 0.02
            return 0.0

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
