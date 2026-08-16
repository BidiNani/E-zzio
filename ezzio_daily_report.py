"""
E-ZZIO Core — Daily Health Report Generator (V8.10)
Condense la télémétrie, l'état des stores, l'intégrité (Drift) et les règles 
en un rapport synthétique journalier pour éviter la saturation des logs.
"""
import os
import sys
import json
import psutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

class DailyReportGenerator:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.reports_dir = self.root_dir / "runtime" / "cognition" / "budget" / "daily_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def get_dir_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return round(total / (1024 * 1024), 2)

    def verify_drift(self) -> str:
        genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        if not genome_path.exists():
            return "MISSING"
        expected = "4b914fb994d1d715"
        actual = hashlib.sha256(genome_path.read_bytes()).hexdigest().lower()
        return "UNCHANGED" if actual.startswith(expected) else "DRIFT_DETECTED"

    def count_overrides(self) -> int:
        ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "human_override_ledger.jsonl"
        if not ledger_path.exists():
            return 0
        count = sum(1 for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip())
        return count

    def generate_report(self) -> Dict[str, Any]:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Hardware snapshot
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        g_disk = psutil.disk_usage(r"G:")

        # Storage snapshot
        mem_store_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "memory_store")
        snapshots_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "snapshots")
        ledgers_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "ecol")

        drift = self.verify_drift()
        overrides = self.count_overrides()

        conclusion = "STABLE" if drift == "UNCHANGED" and mem.percent < 85.0 else "REVIEW_REQUIRED"

        report_data = {
            "report_id": f"DAILY_HEALTH_{timestamp_str}",
            "date": date_str,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "hardware": {
                "cpu_usage_percent": cpu,
                "ram_usage_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "nvme_g_free_gb": round(g_disk.free / (1024**3), 2)
            },
            "memory": {
                "memory_store_mb": mem_store_mb,
                "snapshots_mb": snapshots_mb,
                "ledgers_mb": ledgers_mb
            },
            "security": {
                "drift_status": drift,
                "human_overrides_active": overrides,
                "incidents_count": 0
            },
            "conclusion": conclusion
        }

        report_file = self.reports_dir / f"report_{date_str}.json"
        report_file.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return report_data

def render_daily_report():
    generator = DailyReportGenerator()
    rep = generator.generate_report()
    hw = rep["hardware"]
    mem = rep["memory"]
    sec = rep["security"]

    print("\n" + "="*70)
    print(f" 📊 E-ZZIO DAILY HEALTH REPORT ({rep['date']})")
    print("="*70)
    print(f" Report ID          : {rep['report_id']}")
    print(f" Timestamp UTC      : {rep['timestamp_utc']}")
    print("-" * 70)
    print(f" 💻 MATÉRIEL & RESSOURCES :")
    print(f"   - CPU Ryzen 9      : {hw['cpu_usage_percent']}%")
    print(f"   - RAM 32 Go        : {hw['ram_usage_percent']}% ({hw['ram_used_gb']} Go utilisés)")
    print(f"   - NVMe G: Dispo    : {hw['nvme_g_free_gb']} Go")
    print("-" * 70)
    print(f" 🗄️ CROISSANCE STOCKAGE :")
    print(f"   - Memory Store     : {mem['memory_store_mb']} Mo")
    print(f"   - Snapshots        : {mem['snapshots_mb']} Mo")
    print(f"   - Ledgers ECOL     : {mem['ledgers_mb']} Mo")
    print("-" * 70)
    print(f" 🛡️ SÉCURITÉ & INTÉGRITÉ :")
    print(f"   - Drift Status     : [{sec['drift_status']}]")
    print(f"   - Overrides Actifs : {sec['human_overrides_active']}")
    print(f"   - Incidents        : {sec['incidents_count']}")
    print("-" * 70)
    print(f" 🏁 CONCLUSION        : [{rep['conclusion']}]")
    print("="*70 + "\n")

if __name__ == "__main__":
    render_daily_report()
