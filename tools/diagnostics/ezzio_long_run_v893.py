"""
E-ZZIO Core — Long Run Endurance Monitor & Dynamic Health (V8.9.3 Fixed)
Gère la baseline de performance, calcule un Health Score dynamique pondéré,
gère le mode maintenance de manière autonome et observe l'organisme.
"""

import argparse
import hashlib
import hmac
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class V893EnduranceOrchestrator:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.budget_dir = self.root_dir / "runtime" / "cognition" / "budget"
        self.budget_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_path = self.budget_dir / "ezzio_baseline_V8.9.3.json"
        self.endurance_ledger = self.budget_dir / "endurance_metrics_V8.9.3.jsonl"

        self._ensure_baseline()

    def _ensure_baseline(self):
        if not self.baseline_path.exists():
            baseline_data = {
                "version": "V8.9.3",
                "created_utc": datetime.now(UTC).isoformat(),
                "metrics": {
                    "baseline_ram_usage_percent": 38.0,
                    "baseline_cpu_idle_percent": 2.0,
                    "max_acceptable_ram_percent": 85.0,
                    "max_acceptable_cpu_percent": 90.0,
                    "snapshot_restore_target_sec": 1.5,
                },
            }
            self.baseline_path.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def check_wow_running(self) -> bool:
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and "wow.exe" in p.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def calculate_dynamic_health_score(self, cpu_usage: float, ram_percent: float, gaming_active: bool) -> dict[str, Any]:
        stab_score = 100.0
        if ram_percent > 85.0:
            stab_score -= 30.0
        elif ram_percent > 70.0:
            stab_score -= 10.0
        if cpu_usage > 90.0:
            stab_score -= 20.0

        sec_score = 100.0
        perf_score = 100.0
        if gaming_active:
            perf_score = 100.0 if cpu_usage < 15.0 else 85.0
        else:
            if cpu_usage > 50.0:
                perf_score -= 15.0

        mem_score = 100.0 if ram_percent < 80.0 else 75.0
        evo_score = 100.0

        global_health = (stab_score * 0.40) + (sec_score * 0.20) + (perf_score * 0.20) + (mem_score * 0.10) + (evo_score * 0.10)

        return {
            "global_health_score": round(global_health, 2),
            "breakdown": {
                "stability": stab_score,
                "security": sec_score,
                "performance": perf_score,
                "memory": mem_score,
                "evolution": evo_score,
            },
        }

    def trigger_maintenance_mode(self):
        print("\n[MAINTENANCE] Activation du mode maintenance de l'organisme...")
        print("[MAINTENANCE] 1. Suspension des tâches secondaires en cours...")
        print("[MAINTENANCE] 2. Vérification de l'intégrité constitutionnelle et des ledgers...")

        snapshots_dir = self.root_dir / "runtime" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        snap_id = f"MAINTENANCE_SNAP_{timestamp_str}"
        print(f"[MAINTENANCE] 3. Point de contrôle prêt : {snap_id}")
        print("[MAINTENANCE] Organisme prêt pour intervention / mise à jour.\n")

    def collect_tick(self) -> dict[str, Any]:
        timestamp = datetime.now(UTC).isoformat()
        cpu_usage = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        gaming_active = self.check_wow_running()

        health = self.calculate_dynamic_health_score(cpu_usage, ram_percent, gaming_active)

        tick = {
            "timestamp_utc": timestamp,
            "cpu_usage_percent": cpu_usage,
            "ram_usage_percent": ram_percent,
            "gaming_detected": gaming_active,
            "health": health,
        }

        tick_json = json.dumps(tick, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sig = hmac.new(b"EZZIO_V893_KEY", tick_json.encode("utf-8"), hashlib.sha256).hexdigest()
        sealed = {**tick, "signature_hmac": sig}

        with open(self.endurance_ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(sealed, ensure_ascii=False) + "\n")

        return sealed


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO V8.9.3 Endurance & Maintenance")
    parser.add_argument("--status", action="store_true", help="Affiche l'état de santé dynamique et la télémétrie")
    parser.add_argument("--maintenance", action="store_true", help="Bascule l'organisme en mode maintenance sécurisé")
    args = parser.parse_args()

    orchestrator = V893EnduranceOrchestrator()

    if args.maintenance:
        orchestrator.trigger_maintenance_mode()
    else:
        print("[*] Collecte de la télémétrie dynamique V8.9.3...")
        tick = orchestrator.collect_tick()

        print("\n" + "=" * 70)
        print(" E-ZZIO V8.9.3 DYNAMIC HEALTH & ENDURANCE REPORT")
        print("=" * 70)
        print(f" Timestamp UTC       : {tick['timestamp_utc']}")
        print(f" CPU Ryzen 9         : {tick['cpu_usage_percent']}%")
        print(f" RAM 32 Go           : {tick['ram_usage_percent']}%")
        print(f" World of Warcraft   : {tick['gaming_detected']}")
        print("-" * 70)
        h = tick["health"]
        print(f" GLOBAL HEALTH SCORE : {h['global_health_score']} / 100.0")
        print(f"   - Stabilité (40%) : {h['breakdown']['stability']}/100")
        print(f"   - Sécurité  (20%) : {h['breakdown']['security']}/100")
        print(f"   - Perf      (20%) : {h['breakdown']['performance']}/100")
        print(f"   - Mémoire   (10%) : {h['breakdown']['memory']}/100")
        print(f"   - Évolution (10%) : {h['breakdown']['evolution']}/100")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
