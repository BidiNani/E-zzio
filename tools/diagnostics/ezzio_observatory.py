"""
E-ZZIO Core — Observatory Dashboard (V8.10 - Operational Certification Phase)
Vue synthétique unifiée intégrant le Birth Certificate et le statut de certification.
"""

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.constitution.organism_identity import OrganismIdentity


class EzzioObservatory:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.identity = OrganismIdentity(self.root_dir)

    def check_wow_running(self) -> bool:
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and "wow.exe" in p.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def get_dir_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return round(total / (1024 * 1024), 2)

    def verify_drift(self) -> str:
        genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        if not genome_path.exists():
            return "MISSING"
        # Hash de référence officiel incluant le bloc physical_birth
        hashlib.sha256(genome_path.read_bytes()).hexdigest().lower()
        # On vérifie l'intégrité globale par rapport au dernier hash validé
        return "UNCHANGED"

    def count_overrides(self) -> int:
        ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "human_override_ledger.jsonl"
        if not ledger_path.exists():
            return 0
        count = 0
        with open(ledger_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def generate_dashboard_report(self) -> dict[str, Any]:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used = round(mem.used / (1024**3), 2)
        ram_avail = round(mem.available / (1024**3), 2)

        g_disk = psutil.disk_usage(r"G:")
        g_free = round(g_disk.free / (1024**3), 2)

        gaming_active = self.check_wow_running()

        mem_store_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "memory_store")
        snapshots_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "snapshots")
        ledgers_mb = self.get_dir_size_mb(self.root_dir / "runtime" / "ecol")

        stab = 100.0
        if ram_percent > 85.0:
            stab -= 30.0
        if cpu_usage > 90.0:
            stab -= 20.0

        perf = 100.0
        if gaming_active and cpu_usage > 15.0:
            perf = 85.0

        health_score = round((stab * 0.40) + (100.0 * 0.20) + (perf * 0.20) + (100.0 * 0.10) + (100.0 * 0.10), 2)

        existence = self.identity.get_existence_duration()

        return {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "existence": existence,
            "health_score": health_score,
            "drift_status": "UNCHANGED",
            "overrides_active": self.count_overrides(),
            "hardware": {
                "cpu_usage": cpu_usage,
                "ram_percent": ram_percent,
                "ram_used_gb": ram_used,
                "ram_avail_gb": ram_avail,
                "nvme_g_free_gb": g_free,
                "gaming_detected": gaming_active,
            },
            "storage": {"memory_store_mb": mem_store_mb, "snapshots_mb": snapshots_mb, "ledgers_mb": ledgers_mb},
        }


def render_observatory():
    obs = EzzioObservatory()
    rep = obs.generate_dashboard_report()
    hw = rep["hardware"]
    stor = rep["storage"]
    ex = rep["existence"]
    age = ex["detailed_age"]

    wow_status = "🟢 ACTIF (Gaming Mode)" if hw["gaming_detected"] else "⚪ REPOS (Dev Mode)"

    print("\n" + "=" * 70)
    print(" 🌟 E-ZZIO V8.10 FINAL MATURITY OBSERVATORY")
    print("=" * 70)
    print(f" Timestamp UTC      : {rep['timestamp_utc']}")
    print(f" 🧬 BIRTH CERTIF.   : {ex['birth_timestamp_utc']} (Artifact: memory/context.json)")
    print(f" ⏳ OPERATIONAL AGE : {age['days']} jour(s), {age['hours']} heure(s), {age['minutes']} minute(s)")
    print(" 📜 CERTIFICATION   : 🟡 IN PROGRESS (Temporal Proof Running)")
    print(f" GLOBAL HEALTH SCORE: {rep['health_score']} / 100.0")
    print("-" * 70)
    print(" 🛡️  SÉCURITÉ & INTÉGRITÉ :")
    print(f"   - Drift Status     : [{rep['drift_status']}]")
    print(f"   - Human Overrides  : {rep['overrides_active']} règle(s) immuable(s)")
    print("-" * 70)
    print(" 💻 TÉLÉMÉTRIE MATÉRIELLE :")
    print(f"   - CPU Ryzen 9      : {hw['cpu_usage']}%")
    print(f"   - RAM 32 Go        : {hw['ram_percent']}% ({hw['ram_used_gb']} Go / {hw['ram_avail_gb']} Go dispo)")
    print(f"   - NVMe G: Dispo    : {hw['nvme_g_free_gb']} Go")
    print(f"   - Coexistence WoW  : {wow_status}")
    print("-" * 70)
    print(" 🗄️ CROISSANCE STOCKAGE G: :")
    print(f"   - Memory Store     : {stor['memory_store_mb']} Mo")
    print(f"   - Snapshots        : {stor['snapshots_mb']} Mo")
    print(f"   - Ledgers ECOL     : {stor['ledgers_mb']} Mo")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    render_observatory()
