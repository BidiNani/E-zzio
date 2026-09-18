import logging
import urllib.request
from pathlib import Path

ROOT = Path(r"G:/AI/E-zzio").resolve()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class EzzioWatchdog:
    def __init__(self, max_retries: int = 3, interval_seconds: int = 10):
        self.max_retries = max_retries
        self.interval = interval_seconds
        self.failure_count = 0

    def check_health(self) -> bool:
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/health/readiness")
            with urllib.request.urlopen(req, timeout=3) as res:
                return res.status == 200
        except Exception:
            return False

    def run_once(self) -> dict:
        is_healthy = self.check_health()
        if is_healthy:
            self.failure_count = 0
            return {"status": "HEALTHY", "failures": 0}
        else:
            self.failure_count += 1
            logging.warning(f"Health check failed (attempt {self.failure_count}/{self.max_retries})")
            if self.failure_count >= self.max_retries:
                return {"status": "UNHEALTHY", "failures": self.failure_count, "action": "RESTART_RECOMMENDED"}
            return {"status": "DEGRADED", "failures": self.failure_count}

if __name__ == "__main__":
    wd = EzzioWatchdog()
    res = wd.run_once()
    print("Watchdog check:", res)
