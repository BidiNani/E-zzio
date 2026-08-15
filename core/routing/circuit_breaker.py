"""
E-ZZIO V7.26.0 — Persistent Circuit Breaker
Sauvegarde et restaure l'état des disjoncteurs pour survivre aux reboots.
"""
import time
import json
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_PATH = ROOT_DIR / "runtime" / "state" / "circuit_breakers.json"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_sec: float = 60.0):
        self.threshold = failure_threshold
        self.timeout = recovery_timeout_sec
        self.state_data = self._load_state()

    def _load_state(self) -> dict:
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception: pass
        return {}

    def _save_state(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self.state_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def is_open(self, provider: str) -> bool:
        self.state_data = self._load_state() # Rechargement persistant
        prov_state = self.state_data.get(provider, {"tripped": False, "failures": 0, "trip_time": 0.0})
        
        if not prov_state.get("tripped", False):
            return False
        
        # Vérification du TTL de récupération (Half-Open transition)
        if time.time() - prov_state.get("trip_time", 0.0) > self.timeout:
            prov_state["tripped"] = False
            prov_state["failures"] = 0
            self.state_data[provider] = prov_state
            self._save_state()
            return False
            
        return True

    def record_success(self, provider: str):
        self.state_data[provider] = {"tripped": False, "failures": 0, "trip_time": 0.0}
        self._save_state()

    def record_failure(self, provider: str):
        prov_state = self.state_data.get(provider, {"tripped": False, "failures": 0, "trip_time": 0.0})
        prov_state["failures"] = prov_state.get("failures", 0) + 1
        
        if prov_state["failures"] >= self.threshold:
            prov_state["tripped"] = True
            prov_state["trip_time"] = time.time()
            print(f"[Circuit Breaker] ALERTE PERSISTANTE : '{provider}' disjoncté pour {self.timeout}s.")
            
        self.state_data[provider] = prov_state
        self._save_state()

circuit_breaker = CircuitBreaker()
