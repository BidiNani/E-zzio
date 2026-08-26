"""
E-ZZIO Core — Permanent Benchmark Engine (V8.8 Step 4)
Capteur biologique permanent. Mesure en continu la santé matérielle (Ryzen 9, RAM),
l'état de la mémoire multi-couches, le volume décisionnel et l'intégrité globale.
"""

import sys
import json
import hmac
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.constitution.hardware_resource_governor import HardwareResourceGovernor
from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)


class PermanentBenchmarkEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.hw_gov = HardwareResourceGovernor()
        self.benchmark_ledger = self.root_dir / "runtime" / "cognition" / "budget" / "organism_benchmark_history.jsonl"
        self.benchmark_ledger.parent.mkdir(parents=True, exist_ok=True)

        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("RUN_ORGANISM_BENCHMARK")

    def run_benchmark_tick(self) -> Dict[str, Any]:
        """
        Exécute une passe de mesure biologique globale de l'organisme.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Collecte télémétrie matérielle
        hw_telemetry = self.hw_gov.get_system_telemetry()

        # 2. Inspection de la mémoire multi-couches (L0-L5 store)
        memory_store_dir = self.root_dir / "runtime" / "memory_store"
        total_mem_records = 0
        tiers_count = {}
        if memory_store_dir.exists():
            for tier_dir in memory_store_dir.iterdir():
                if tier_dir.is_dir():
                    count = len(list(tier_dir.glob("*.json")))
                    tiers_count[tier_dir.name] = count
                    total_mem_records += count

        # 3. Inspection du Decision Ledger (Vérification Cryptographique)
        total_decisions = 0
        try:
            from core.cognition.decision_ledger import DecisionLedgerEngine
            dle = DecisionLedgerEngine(root_dir=self.root_dir)
            total_decisions = len(dle.query_decisions(limit=1000000))
        except Exception as dle_err:
            logger.error(f"[BENCHMARK] Could not query verified decision ledger: {dle_err}")
            total_decisions = 0

        # 4. Calcul de l'indice de santé global (Organism Health Score)
        ram_percent = hw_telemetry["ram_usage_percent"]
        cpu_percent = hw_telemetry["cpu_system_usage_percent"]

        health_score = 100.0
        if ram_percent > 85.0:
            health_score -= 15.0
        if cpu_percent > 90.0:
            health_score -= 10.0

        benchmark_data = {
            "timestamp_utc": timestamp,
            "hardware": {
                "cpu_usage_percent": cpu_percent,
                "ram_usage_percent": ram_percent,
                "ram_available_gb": hw_telemetry["ram_available_gb"],
                "gaming_mode_active": hw_telemetry["gaming_detected"],
                "active_profile": hw_telemetry["profile"],
            },
            "memory": {"total_records": total_mem_records, "tiers_distribution": tiers_count},
            "cognition": {"total_recorded_decisions": total_decisions},
            "organism_health_score": round(health_score, 2),
            "status": "HEALTHY_OPTIMIZED" if health_score >= 80.0 else "DEGRADED",
        }

        # Scellement HMAC du benchmark
        bench_json = json.dumps(benchmark_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sec_key = b"EZZIO_BENCHMARK_ROOT_KEY_2026"
        signature = hmac.new(sec_key, bench_json.encode("utf-8"), hashlib.sha256).hexdigest()

        sealed_benchmark = {**benchmark_data, "signature_hmac": signature}

        # Validation No-Bypass via ECOL en utilisant la source "system_core"
        payload = {
            "source_component": "system_core",
            "action": "RUN_ORGANISM_BENCHMARK",
            "task_description": f"Exécution benchmark biologique (Score: {health_score})",
            "priority": "normal",
            "risk_level": "low",
            "estimated_cost": 50,
        }

        def commit_benchmark():
            with open(self.benchmark_ledger, "a", encoding="utf-8") as f:
                f.write(json.dumps(sealed_benchmark, ensure_ascii=False) + "\n")
            return sealed_benchmark

        result = self.gateway.execute_via_gateway(action="RUN_ORGANISM_BENCHMARK", payload=payload, target_func=commit_benchmark)

        return result


def test_benchmark():
    print("[*] Exécution du Permanent Benchmark Engine (V8.8 Step 4)...")
    engine = PermanentBenchmarkEngine()

    res = engine.run_benchmark_tick()

    print("\n" + "=" * 70)
    print(" E-ZIO PERMANENT BENCHMARK REPORT (V8.8)")
    print("=" * 70)
    print(f" Timestamp UTC       : {res['timestamp_utc']}")
    print(f" Profil Matériel     : {res['hardware']['active_profile']}")
    print(f" Gaming Détecté      : {res['hardware']['gaming_mode_active']}")
    print(
        f" Charge CPU / RAM    : {res['hardware']['cpu_usage_percent']}% / {res['hardware']['ram_usage_percent']}% ({res['hardware']['ram_available_gb']} Go dispo)"
    )
    print(f" Mémoire Multi-Niveaux: {res['memory']['total_records']} enregistrement(s) actif(s)")
    print(f" Décisions Unifiées  : {res['cognition']['total_recorded_decisions']} décision(s) tracée(s)")
    print(f" ORGANISM HEALTH     : {res['organism_health_score']} / 100 [{res['status']}]")
    print(f" SIGNATURE HMAC      : {res['signature_hmac'][:32]}...")
    print("=" * 70)


if __name__ == "__main__":
    test_benchmark()
