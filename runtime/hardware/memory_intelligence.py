import os
import time
import psutil

class MemoryIntelligenceEngine:
    """
    Moteur V5.1.1 d'intelligence mémoire recalibré.
    Proportionne la sensibilité d'accélération (lambda = 0.005) pour éviter
    les faux positifs tout en maintenant une détection immédiate des spikes.
    """
    def __init__(self, budget_mb: float = 10240.0):
        self.budget_mb = budget_mb
        self.target_pid = os.getpid()
        self.process = psutil.Process(self.target_pid)
        self.last_rss_mb = self._get_rss_mb()
        self.last_time = time.time()
        
        # Coefficient lissé : 0.005 (Un spike de 200 MB/s ajoute 1.0 à l'indice OOM)
        self.lambda_weight = 0.005 

    def update_target_pid(self, pid: int):
        if pid and pid != self.target_pid:
            try:
                self.process = psutil.Process(pid)
                self.target_pid = pid
                self.last_rss_mb = self._get_rss_mb()
                self.last_time = time.time()
            except psutil.NoSuchProcess:
                pass

    def _get_rss_mb(self) -> float:
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def evaluate_state(self) -> dict:
        now = time.time()
        dt = max(0.001, now - self.last_time)
        
        current_rss_mb = self._get_rss_mb()
        d_rss_dt = (current_rss_mb - self.last_rss_mb) / dt
        
        self.last_rss_mb = current_rss_mb
        self.last_time = now
        
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        free_ram_gb = vm.available / (1024**3)
        commit_pressure = swap.percent / 100.0 if swap.total > 0 else 0.0
        
        # Calcul de l'indice OOM recalibré
        base_usage = current_rss_mb / self.budget_mb
        oom_index = base_usage + (self.lambda_weight * max(0.0, d_rss_dt))
        oom_index = round(min(1.0, max(0.0, oom_index)), 3)
        
        is_critical = oom_index > 0.85 or free_ram_gb < 2.0 or commit_pressure > 0.90
        
        return {
            "target_pid": self.target_pid,
            "rss_mb": round(current_rss_mb, 2),
            "d_rss_dt_mbs": round(d_rss_dt, 2),
            "free_ram_gb": round(free_ram_gb, 2),
            "commit_pressure": round(commit_pressure, 3),
            "oom_index": oom_index,
            "critical_oom_risk": is_critical
        }
