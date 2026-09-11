"""
E-ZZIO V7.23.0.9 — Granular Health & Performance Telemetry
Génère des scores de santé détaillés et synchronise provider_performance.json.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from providers.gemini_provider import GeminiProvider
from providers.groq_provider import GroqProvider

HEALTH_LOG_PATH = ROOT_DIR / "runtime" / "metrics" / "provider_health_status.json"
PERFORMANCE_LOG_PATH = ROOT_DIR / "runtime" / "metrics" / "provider_performance.json"


class ProviderHealthMonitor:
    def __init__(self):
        self.providers = {"gemini": GeminiProvider(), "groq": GroqProvider()}

    def _load_performance(self) -> dict:
        if PERFORMANCE_LOG_PATH.exists():
            try:
                return json.loads(PERFORMANCE_LOG_PATH.read_text(encoding="utf-8")).get("providers", {})
            except Exception:
                pass
        return {}

    def check_provider_health(self, name: str) -> dict:
        provider = self.providers.get(name)
        if not provider:
            return {"healthy": False, "error": f"Fournisseur '{name}' inconnu"}

        base_health = provider.health()
        pool_size = base_health.get("pool_size", 0)
        has_keys = pool_size > 0
        last_err = base_health.get("last_error")

        # Chargement de la télémétrie de performance associée
        perf = self._load_performance().get(name, {"calls": 0, "success": 0, "errors": 0, "avg_latency_ms": 0.0})
        total_calls = perf.get("calls", 0)
        success_calls = perf.get("success", 0)

        availability = 1.0 if has_keys and not last_err else (0.5 if has_keys else 0.0)
        success_rate = (success_calls / total_calls) if total_calls > 0 else 1.0

        # Calcul des scores granulaires préparant le Self-Tuning Router
        health_score = round((availability * 0.5) + (success_rate * 0.5), 3)
        quota_state = "available" if has_keys else "exhausted"

        return {
            "provider": name,
            "healthy": has_keys,
            "health_score": health_score,
            "availability": availability,
            "quota_state": quota_state,
            "success_rate": success_rate,
            "pool_size": pool_size,
            "last_error": last_err,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def run_full_health_check(self) -> dict:
        report = {"schema_version": "V1.0-GRANULAR-HEALTH", "timestamp": datetime.now(timezone.utc).isoformat(), "providers": {}}

        for name in self.providers.keys():
            report["providers"][name] = self.check_provider_health(name)

        HEALTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_LOG_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report


if __name__ == "__main__":
    print("[E-ZZIO V7.23.0.9] Exécution du Health Monitor Granulaire...")
    monitor = ProviderHealthMonitor()
    res = monitor.run_full_health_check()
    print(json.dumps(res, indent=2))
