"""
E-ZZIO Core — Organism Endurance & Chaos Certification Harness (V8.9.1)
Exécute la batterie de tests d'intégrité, simule un chaos contrôlé (corruption / résilience)
et délivre le certificat officiel de l'organisme E-zzio.
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.self_healing_engine import SelfHealingEngine
from core.constitution.snapshot_restore_engine import SnapshotRestoreEngine
from ezzio_kernel import OrganismKernel

logging.basicConfig(level=logging.WARNING)


class OrganismCertificationHarness:
    def __init__(self):
        self.kernel = OrganismKernel()
        self.healer = SelfHealingEngine()
        self.restorer = SnapshotRestoreEngine()

    def run_certification_suite(self) -> dict[str, Any]:
        results = {}

        # 1. Test Identité & Génome
        identity = self.kernel.verify_identity()
        results["Identity"] = "PASS" if identity["status"] == "VALID" else "FAIL"

        # 2. Test ECOL & Constitution
        status = self.kernel.get_organism_status()
        results["ECOL_Gateway"] = "PASS" if status["ecol_gateway"]["status"] == "ACTIVE" else "FAIL"
        results["Constitution"] = "PASS" if status["constitution"]["status"] == "VALID" else "FAIL"

        # 3. Test Matériel / Coexistence
        hw = status["hardware"]
        results["Hardware_Coexistence"] = "PASS" if "GAMING" in hw["profile"] or "NORMAL" in hw["profile"] else "FAIL"

        # 4. Test Mémoire & Décisions
        results["Memory_Subsystem"] = "PASS" if status["memory"]["status"] == "ONLINE" else "FAIL"
        results["Decision_Ledger"] = "PASS" if status["decision_ledger"]["status"] in ("ACTIVE_AND_VERIFIED", "ACTIVE") and not status["decision_ledger"].get("error") else "FAIL"

        # 5. Test Chaos Contrôlé & Self-Healing
        try:
            chaos_res = self.healer.handle_incident(
                incident_type="MEMORY_CORRUPTION",
                component="endurance_test_harness.py",
                error_details="Simulation de chaos contrôlé pour validation de résilience V8.9.1.",
            )
            results["Chaos_Self_Healing"] = "PASS" if chaos_res["status"] == "HEALED_AND_ISOLATED" else "FAIL"
        except Exception as e:
            results["Chaos_Self_Healing"] = f"FAIL: {e}"

        # 6. Test Time Travel / Snapshot Restore
        try:
            snapshots_dir = ROOT_DIR / "runtime" / "snapshots"
            snaps = [d.name for d in snapshots_dir.iterdir() if d.is_dir()] if snapshots_dir.exists() else []
            if snaps:
                latest = sorted(snaps)[-1]
                restore_res = self.restorer.restore_snapshot(latest)
                results["Snapshot_Restore"] = "PASS" if restore_res["status"] == "RESTORED_SUCCESS" else "FAIL"
            else:
                results["Snapshot_Restore"] = "SKIPPED_NO_SNAPSHOT"
        except Exception as e:
            results["Snapshot_Restore"] = f"FAIL: {e}"

        # Calcul du score global
        passes = sum(1 for v in results.values() if v == "PASS")
        total = len(results)
        global_status = "OPERATIONAL & CERTIFIED" if passes >= (total - 1) else "DEGRADED"

        certificate = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "certification_level": "V8.9.1-ENDURANCE-CHAOS",
            "tests": results,
            "passed_count": passes,
            "total_tests": total,
            "global_state": global_status,
        }
        return certificate


def render_certificate():
    print("\n[*] Lancement du protocole de certification V8.9.1...")
    harness = OrganismCertificationHarness()
    cert = harness.run_certification_suite()

    print("\n" + "=" * 70)
    print(" E-ZZIO V8.9 ORGANISM INTEGRATION CERTIFICATE")
    print("=" * 70)
    print(f" Timestamp UTC      : {cert['timestamp_utc']}")
    print(f" Niveau de certif   : {cert['certification_level']}")
    print("-" * 70)
    for test_name, res in cert["tests"].items():
        icon = "[PASS]" if res == "PASS" else "[WARN]" if "SKIPPED" in res else "[FAIL]"
        print(f" {icon:<7} {test_name:<25} : {res}")
    print("-" * 70)
    print(f" Tests validés      : {cert['passed_count']} / {cert['total_tests']}")
    print(f" ÉTAT GLOBAL        : {cert['global_state']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    render_certificate()
