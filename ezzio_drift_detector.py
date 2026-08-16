"""
E-ZZIO Core — Drift Detector (V8.9.4.1)
Surveille l'intégrité des fichiers critiques de l'organisme et classifie 
les modifications (Inchangé, Évolution autorisée, Override humain, Dérive inconnue).
"""
import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

class DriftDetectorEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.baseline_path = self.root_dir / "runtime" / "cognition" / "budget" / "approved_hashes.json"
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_baseline()

    def _ensure_baseline(self):
        """Initialise la baseline des hashes approuvés si absente."""
        if not self.baseline_path.exists():
            baseline = {
                "version": "V8.9.4.1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "files": {}
            }
            critical_files = [
                self.root_dir / "core" / "constitution" / "ezzio_genome.json",
                self.root_dir / "core" / "constitution" / "ezzio_global_framework.py"
            ]
            for f in critical_files:
                if f.exists():
                    rel = f.relative_to(self.root_dir).as_posix()
                    h = hashlib.sha256(f.read_bytes()).hexdigest().lower()
                    baseline["files"][rel] = h
            self.baseline_path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")

    def scan_and_classify(self) -> Dict[str, Any]:
        """Scanne les fichiers critiques et classifie les états d'intégrité."""
        baseline_data = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        stored_hashes = baseline_data.get("files", {})

        critical_files = [
            self.root_dir / "core" / "constitution" / "ezzio_genome.json",
            self.root_dir / "core" / "constitution" / "ezzio_global_framework.py"
        ]

        report = {}
        for f in critical_files:
            if not f.exists():
                continue
            rel = f.relative_to(self.root_dir).as_posix()
            current_hash = hashlib.sha256(f.read_bytes()).hexdigest().lower()
            expected_hash = stored_hashes.get(rel)

            if expected_hash is None:
                classification = "NEW_UNTRACKED_FILE"
            elif current_hash == expected_hash:
                classification = "UNCHANGED"
            else:
                classification = "UNKNOWN_DRIFT_DETECTED"

            report[rel] = {
                "status": classification,
                "current_hash": current_hash[:16] + "...",
                "expected_hash": expected_hash[:16] + "..." if expected_hash else "N/A"
            }

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scan_mode": "CLASSIFICATION_NON_BLOCKING",
            "report": report
        }

def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Drift Detector (V8.9.4.1)")
    parser.add_argument("--scan", action="store_true", help="Exécute un scan d'intégrité et affiche la classification")
    args = parser.parse_args()

    detector = DriftDetectorEngine()
    result = detector.scan_and_classify()

    print("\n" + "="*70)
    print(" E-ZIO DRIFT DETECTOR REPORT (V8.9.4.1)")
    print("="*70)
    print(f" Timestamp UTC      : {result['timestamp_utc']}")
    print(f" Mode de scan       : {result['scan_mode']}")
    print("-" * 70)
    for filepath, info in result["report"].items():
        status = info["status"]
        icon = "🟢" if status == "UNCHANGED" else "🟡" if "NEW" in status else "🔴"
        print(f" {icon} {filepath}")
        print(f"    Statut      : {status}")
        print(f"    Actuel      : {info['current_hash']}")
        print(f"    Attendu     : {info['expected_hash']}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
