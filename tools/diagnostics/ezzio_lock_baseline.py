"""
E-ZZIO Core — Baseline Lock & Freeze Protocol (V8.9.4)
Capture et scelle l'état de référence de l'organisme (hashes constitutionnels,
état initial de la mémoire, configuration matérielle) pour lancer la campagne de certification.
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class BaselineLockProtocol:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.budget_dir = self.root_dir / "runtime" / "cognition" / "budget"
        self.budget_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_file = self.budget_dir / "EZZIO_V8.9.4_BASELINE.json"

    def get_file_hash(self, path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest().lower()

    def get_dir_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return round(total / (1024 * 1024), 2)

    def capture_baseline(self) -> dict[str, Any]:
        genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        framework_path = self.root_dir / "core" / "constitution" / "ezzio_global_framework.py"

        baseline_data = {
            "baseline_id": "EZZIO_V8.9.4_BASELINE",
            "locked_utc": datetime.now(UTC).isoformat(),
            "status": "CONSTITUTION_FROZEN_AND_LOCKED",
            "integrity": {"genome_sha256": self.get_file_hash(genome_path), "framework_sha256": self.get_file_hash(framework_path)},
            "hardware_profile": {
                "cpu": "AMD Ryzen 9 5900X (24 threads)",
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "gpu_policy": "GTX 1650 4Go 100% Reserved for Gaming (Immutable Override HW-001)",
                "storage_drive": "NVMe G:",
            },
            "initial_storage_state": {
                "memory_store_mb": self.get_dir_size_mb(self.root_dir / "runtime" / "memory_store"),
                "snapshots_mb": self.get_dir_size_mb(self.root_dir / "runtime" / "snapshots"),
                "ledgers_mb": self.get_dir_size_mb(self.root_dir / "runtime" / "ecol"),
            },
            "stability_index_target": {
                "system_stability": 100.0,
                "integrity": 100.0,
                "recovery": 100.0,
                "memory": 98.0,
                "performance": 99.0,
                "discretion": 100.0,
            },
        }

        self.baseline_file.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return baseline_data


def lock_baseline_cli():
    print("[*] Verrouillage et scellement de la baseline V8.9.4...")
    locker = BaselineLockProtocol()
    data = locker.capture_baseline()

    print("\n" + "=" * 70)
    print(" 🔒 E-ZZIO V8.9.4 BASELINE LOCKED & FROZEN")
    print("=" * 70)
    print(f" Baseline ID        : {data['baseline_id']}")
    print(f" Verrouillé UTC     : {data['locked_utc']}")
    print(f" Statut             : {data['status']}")
    print("-" * 70)
    print(" 🧬 HASHES CONSTITUTIONNELS :")
    print(f"   - Génome         : {data['integrity']['genome_sha256'][:24]}...")
    print(f"   - Framework      : {data['integrity']['framework_sha256'][:24]}...")
    print("-" * 70)
    print(" 🛡️  POLITIQUE MATÉRIELLE :")
    print(f"   - CPU            : {data['hardware_profile']['cpu']}")
    print(f"   - GPU Policy     : {data['hardware_profile']['gpu_policy']}")
    print("-" * 70)
    print(" 🗄️ ÉTAT INITIAL STOCKAGE :")
    print(f"   - Memory Store   : {data['initial_storage_state']['memory_store_mb']} Mo")
    print(f"   - Snapshots      : {data['initial_storage_state']['snapshots_mb']} Mo")
    print(f"   - Ledgers ECOL   : {data['initial_storage_state']['ledgers_mb']} Mo")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    lock_baseline_cli()
