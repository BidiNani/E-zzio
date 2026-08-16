"""
E-ZZIO Core — Long Run Monitor (V8.9.2 Read-Only)
Capteur d'observation longue durée. Mesure en continu le Ryzen 9, la RAM,
l'espace NVMe, la coexistence Gaming (WoW) et consigne les métriques dans un ledger scellé.
"""
import os
import sys
import json
import psutil
import hmac
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

class LongRunMonitor:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.metrics_ledger = self.root_dir / "runtime" / "cognition" / "budget" / "long_run_metrics.jsonl"
        self.metrics_ledger.parent.mkdir(parents=True, exist_ok=True)

    def check_wow_running(self) -> bool:
        for p in psutil.process_iter(['name']):
            try:
                if p.info['name'] and 'wow.exe' in p.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def get_directory_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total_bytes = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return round(total_bytes / (1024 * 1024), 2)

    def collect_metrics_tick(self) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # CPU telemetry
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        freq_mhz = cpu_freq.current if cpu_freq else 0.0

        # RAM telemetry
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used_gb = round(mem.used / (1024**3), 2)
        ram_avail_gb = round(mem.available / (1024**3), 2)
        
        if ram_percent < 60.0:
            ram_pressure = "NORMAL"
        elif ram_percent < 85.0:
            ram_pressure = "ELEVATED"
        elif ram_percent < 95.0:
            ram_pressure = "ALERTE"
        else:
            ram_pressure = "CRITIQUE"

        # NVMe G: Storage telemetry
        g_disk = psutil.disk_usage(r"G:")
        g_free_gb = round(g_disk.free / (1024**3), 2)
        g_total_gb = round(g_disk.total / (1024**3), 2)

        memory_store_size = self.get_directory_size_mb(self.root_dir / "runtime" / "memory_store")
        snapshots_size = self.get_directory_size_mb(self.root_dir / "runtime" / "snapshots")
        ledgers_size = self.get_directory_size_mb(self.root_dir / "runtime" / "ecol" / "evolution_ledger")

        # Gaming Coexistence detection
        gaming_active = self.check_wow_running()
        profile = "GAMING_COEXISTENCE_MODE" if gaming_active else "DEVELOPMENT_MODE"

        tick_data = {
            "timestamp_utc": timestamp,
            "mode": "READ_ONLY_OBSERVATION",
            "hardware": {
                "cpu_usage_percent": cpu_usage,
                "cpu_freq_mhz": freq_mhz,
                "ram_usage_percent": ram_percent,
                "ram_used_gb": ram_used_gb,
                "ram_available_gb": ram_avail_gb,
                "ram_pressure": ram_pressure,
                "nvme_g_free_gb": g_free_gb,
                "nvme_g_total_gb": g_total_gb
            },
            "storage_growth_mb": {
                "memory_store_mb": memory_store_size,
                "snapshots_mb": snapshots_size,
                "ledgers_mb": ledgers_size
            },
            "coexistence": {
                "gaming_detected": gaming_active,
                "active_profile": profile
            }
        }

        # Scellement HMAC du tick
        tick_json = json.dumps(tick_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        signature = hmac.new(b"EZZIO_LONG_RUN_KEY_2026", tick_json.encode("utf-8"), hashlib.sha256).hexdigest()
        sealed_tick = {**tick_data, "signature_hmac": signature}

        with open(self.metrics_ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(sealed_tick, ensure_ascii=False) + "\n")

        return sealed_tick

def render_monitor_cli():
    print("[*] Collecte de la télémétrie Long Run (V8.9.2 Read-Only)...")
    monitor = LongRunMonitor()
    tick = monitor.collect_metrics_tick()

    hw = tick["hardware"]
    stor = tick["storage_growth_mb"]
    coex = tick["coexistence"]

    print("\n" + "="*70)
    print(" E-ZZIO LONG RUN MONITOR REPORT (V8.9.2)")
    print("="*70)
    print(f" Timestamp UTC       : {tick['timestamp_utc']}")
    print(f" Mode d'exécution    : {tick['mode']}")
    print("-" * 70)
    print(f" CPU Ryzen 9 Usage   : {hw['cpu_usage_percent']}% (Fréquence : {hw['cpu_freq_mhz']} MHz)")
    print(f" RAM 32 Go Utilisation : {hw['ram_usage_percent']}% ({hw['ram_used_gb']} Go utilisés / {hw['ram_available_gb']} Go dispo)")
    print(f" Pression Mémoire    : [{hw['ram_pressure']}]")
    print(f" NVMe G: Espace libre  : {hw['nvme_g_free_gb']} Go / {hw['nvme_g_total_gb']} Go")
    print("-" * 70)
    print(f" Croissance Stockage :")
    print(f"   - Memory Store    : {stor['memory_store_mb']} Mo")
    print(f"   - Snapshots       : {stor['snapshots_mb']} Mo")
    print(f"   - Ledgers ECOL    : {stor['ledgers_mb']} Mo")
    print("-" * 70)
    print(f" Profil Coexistence  : {coex['active_profile']}")
    print(f" World of Warcraft   : {'DÉTECTÉ (True)' if coex['gaming_detected'] else 'NON DÉTECTÉ (False)'}")
    print(f" Signature HMAC      : {tick['signature_hmac'][:32]}...")
    print("="*70 + "\n")

if __name__ == "__main__":
    render_monitor_cli()
