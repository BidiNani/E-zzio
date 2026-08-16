import time
import threading

class ActiveMemoryActuator:
    """
    Régulateur actif de mémoire E-ZZIO V5.2.
    Ajuste dynamiquement les contraintes du moteur de stockage (ConcurrentSegmentedEngine)
    en fonction de l'indice OOM et de la pente d'allocation mesurés par MemoryIntelligenceEngine.
    """
    def __init__(self, engine_ref, memory_engine_ref, check_interval: float = 0.5):
        self.engine = engine_ref
        self.memory_engine = memory_engine_ref
        self.check_interval = check_interval
        
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.current_regulation_tier = "NOMINAL"
        
        self.monitor_thread = threading.Thread(target=self._actuator_loop, daemon=True)

    def start(self):
        if not self.monitor_thread.is_alive():
            self.monitor_thread.start()

    def _actuator_loop(self):
        while not self._stop_event.is_set():
            try:
                self.apply_regulation_tick()
            except Exception as e:
                print(f"[ACTUATOR WARN] Erreur lors du tick de régulation : {e}", flush=True)
            time.sleep(self.check_interval)

    def apply_regulation_tick(self) -> dict:
        with self._lock:
            metrics = self.memory_engine.evaluate_state()
            oom_index = metrics.get("oom_index", 0.0)
            is_critical = metrics.get("critical_oom_risk", False)

            prev_tier = self.current_regulation_tier

            if is_critical or oom_index > 0.85:
                # Tier CRITIQUE : Réduction drastique de la taille des lots, temporisation d'ingestion
                self.current_regulation_tier = "CRITICAL"
                self.engine.max_batch_size = 250
                self.engine.max_batch_delay = 0.05
            elif oom_index > 0.60:
                # Tier TENDEUR : Lotissement intermédiaire
                self.current_regulation_tier = "MODERATE"
                self.engine.max_batch_size = 1000
                self.engine.max_batch_delay = 0.02
            else:
                # Tier NOMINAL : Ingestion fluide maximale
                self.current_regulation_tier = "NOMINAL"
                self.engine.max_batch_size = 2000
                self.engine.max_batch_delay = 0.01

            if prev_tier != self.current_regulation_tier:
                print(f"[MEMORY ACTUATOR] Transition : {prev_tier} -> {self.current_regulation_tier} | Batch Size : {self.engine.max_batch_size} | Delay : {self.engine.max_batch_delay}s", flush=True)

            return {
                "tier": self.current_regulation_tier,
                "oom_index": oom_index,
                "max_batch_size": getattr(self.engine, "max_batch_size", 2000),
                "max_batch_delay": getattr(self.engine, "max_batch_delay", 0.01)
            }

    def stop(self):
        self._stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
